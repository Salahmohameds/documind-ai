"""OCI Generative AI provider - IAM-authenticated, no API keys anywhere.

Status
------
Written against the documented shape of the ``oci`` Python SDK
(``oci.generative_ai_inference``) and **not yet executed against a live
endpoint**, because decision D1 is open: nobody on the team has run
``oci iam region-subscription list`` yet. Every call site that needs
confirming against the pinned SDK version is marked ``VERIFY-D1``.

Region vs compartment - the thing that unblocks this
----------------------------------------------------
Compartments in OCI are **global**; the SDK client is separately pointed at a
**regional endpoint**. ``me-jeddah-1`` does not host Generative AI, but that
does not force the project off OCI: if the tenancy is subscribed to any region
that does host it (``me-riyadh-1`` is the nearest candidate), this adapter can
target that region's endpoint while passing a Jeddah compartment OCID. Dynamic
group unchanged, policy unchanged, no data leaves the tenancy.

That is why ``OCI_REGION`` and ``OCI_COMPARTMENT_ID`` are independent settings
and neither is derived from the other.

Authentication
--------------
Never an API key. In order of preference:

* ``workload`` - OKE workload identity (production; the pod assumes a
  dynamic-group identity, nothing is mounted that a ``kubectl exec`` could steal)
* ``instance`` - instance principal (VM fallback)
* ``config``   - ``~/.oci/config`` - **local development only**, and refused
  outright if it is selected while running inside a cluster.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.adapters.base import AIProvider, ChatMessage, ChatResult, EmbedResult, estimate_tokens
from app.errors import ProviderConfigurationError, ProviderUnavailableError

logger = logging.getLogger("ai-service")

#: Regions that host OCI Generative AI. Used only to fail fast with a useful
#: message; the authoritative check is `oci iam region-subscription list`
#: cross-referenced with Oracle's availability table. Keep in sync with ADR-006.
GENAI_REGIONS = frozenset(
    {
        "sa-saopaulo-1",
        "eu-frankfurt-1",
        "ap-hyderabad-1",
        "ap-osaka-1",
        "me-riyadh-1",
        "me-abudhabi-1",
        "me-dubai-1",
        "uk-london-1",
        "us-ashburn-1",
        "us-chicago-1",
        "us-phoenix-1",
    }
)


class OCIGenAIProvider(AIProvider):
    name = "oci"
    is_external = True

    def __init__(
        self,
        *,
        region: str,
        compartment_id: str,
        auth_mode: str,
        model_name: str,
        embedding_model: str,
        embedding_dim: int,
        timeout_s: float,
        serving_mode: str = "ON_DEMAND",
        endpoint: str = "",
    ) -> None:
        if not region:
            raise ProviderConfigurationError("OCI_REGION is required when AI_BACKEND=oci")
        if not compartment_id:
            raise ProviderConfigurationError(
                "OCI_COMPARTMENT_ID is required when AI_BACKEND=oci"
            )
        if region not in GENAI_REGIONS:
            logger.warning(
                "oci_region_not_on_genai_list",
                extra={"region": region, "hint": "see ADR-006; verify with region-subscription list"},
            )

        self._region = region
        self._compartment_id = compartment_id
        self._auth_mode = auth_mode
        self._chat_model = model_name
        self._embed_model = embedding_model
        self._dim = embedding_dim
        self._timeout_s = timeout_s
        self._serving_mode = serving_mode
        self._endpoint = endpoint or f"https://inference.generativeai.{region}.oci.oraclecloud.com"
        self._control_endpoint = f"https://generativeai.{region}.oci.oraclecloud.com"

        self._oci = self._import_sdk()
        self._signer, self._config = self._build_auth()
        self._client = self._build_inference_client()
        self._control_client: Any | None = None

    # -- identity ---------------------------------------------------------
    @property
    def chat_model(self) -> str:
        return self._chat_model

    @property
    def embed_model(self) -> str:
        return self._embed_model

    @property
    def embed_dim(self) -> int:
        return self._dim

    # -- construction -----------------------------------------------------
    @staticmethod
    def _import_sdk() -> Any:
        try:
            import oci  # noqa: PLC0415 - optional dependency, imported on demand
        except ImportError as exc:  # pragma: no cover - exercised only with AI_BACKEND=oci
            raise ProviderConfigurationError(
                "AI_BACKEND=oci but the 'oci' package is not installed. "
                "Build the image with --build-arg INSTALL_OCI=true, or "
                "pip install -r requirements-oci.txt."
            ) from exc
        return oci

    def _build_auth(self) -> tuple[Any, dict[str, Any]]:
        """Return ``(signer, config)`` for the selected auth mode."""
        oci = self._oci

        if self._auth_mode == "workload":
            # OKE workload identity: the pod's service account is mapped to a
            # dynamic group. Nothing is written to disk and no key exists to leak.
            signer = oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
            return signer, {"region": self._region}

        if self._auth_mode == "instance":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            return signer, {"region": self._region}

        if self._auth_mode == "config":
            # Refuse the developer path inside a cluster: it would mean a key
            # file had been baked into an image or mounted from a Secret.
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                raise ProviderConfigurationError(
                    "OCI_AUTH_MODE=config is for local development only and must "
                    "not be used inside Kubernetes. Use 'workload'."
                )
            config = oci.config.from_file()
            config["region"] = self._region or config.get("region", "")
            return None, config

        raise ProviderConfigurationError(f"Unknown OCI_AUTH_MODE: {self._auth_mode}")

    def _build_inference_client(self) -> Any:
        from oci.generative_ai_inference import GenerativeAiInferenceClient  # noqa: PLC0415

        kwargs: dict[str, Any] = {
            "config": self._config,
            "service_endpoint": self._endpoint,
            # The SDK retries internally; we do our own bounded retry in
            # app.resilience, so disable the hidden one to keep the timeout
            # budget honest.
            "retry_strategy": self._oci.retry.NoneRetryStrategy(),
            "timeout": (self._timeout_s, self._timeout_s),
        }
        if self._signer is not None:
            kwargs["signer"] = self._signer
        return GenerativeAiInferenceClient(**kwargs)

    def _get_control_client(self) -> Any:
        """Control-plane client, used only by :meth:`probe`."""
        if self._control_client is None:
            from oci.generative_ai import GenerativeAiClient  # noqa: PLC0415

            kwargs: dict[str, Any] = {
                "config": self._config,
                "service_endpoint": self._control_endpoint,
                "retry_strategy": self._oci.retry.NoneRetryStrategy(),
                "timeout": (5.0, 5.0),
            }
            if self._signer is not None:
                kwargs["signer"] = self._signer
            self._control_client = GenerativeAiClient(**kwargs)
        return self._control_client

    # -- serving mode -----------------------------------------------------
    def _serving(self, model_id: str) -> Any:
        from oci.generative_ai_inference.models import (  # noqa: PLC0415
            DedicatedServingMode,
            OnDemandServingMode,
        )

        if self._serving_mode == "DEDICATED":
            return DedicatedServingMode(endpoint_id=model_id)
        return OnDemandServingMode(model_id=model_id)

    # -- chat -------------------------------------------------------------
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        task: str = "generic",
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        # task/context are mock-only hints; a real model gets the prompt itself.
        from oci.generative_ai_inference.models import ChatDetails  # noqa: PLC0415

        chat_request = self._build_chat_request(messages, temperature, max_tokens)
        details = ChatDetails(
            compartment_id=self._compartment_id,
            serving_mode=self._serving(self._chat_model),
            chat_request=chat_request,
        )

        try:
            response = self._client.chat(details)
        except Exception as exc:  # SDK raises ServiceError and transport errors
            raise ProviderUnavailableError(f"OCI Generative AI chat failed: {exc}") from exc

        text = self._extract_text(response)
        tokens_in, tokens_out, reported = self._extract_usage(response)
        if not reported:
            tokens_in = sum(estimate_tokens(m.content) for m in messages)
            tokens_out = estimate_tokens(text)

        return ChatResult(
            text=text,
            model=self._chat_model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated=not reported,
        )

    def _build_chat_request(
        self, messages: list[ChatMessage], temperature: float, max_tokens: int
    ) -> Any:
        """Cohere and the generic (Llama / Gemini / Grok) families differ.

        VERIFY-D1: confirm the request class for whichever model D1 selects.
        """
        from oci.generative_ai_inference.models import (  # noqa: PLC0415
            BaseChatRequest,
            CohereChatRequest,
            GenericChatRequest,
            Message,
            TextContent,
        )

        if "cohere" in self._chat_model.lower():
            system = "\n\n".join(m.content for m in messages if m.role == "system")
            user = "\n\n".join(m.content for m in messages if m.role != "system")
            return CohereChatRequest(
                api_format=BaseChatRequest.API_FORMAT_COHERE,
                preamble_override=system or None,
                message=user,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return GenericChatRequest(
            api_format=BaseChatRequest.API_FORMAT_GENERIC,
            messages=[
                Message(role=m.role.upper(), content=[TextContent(text=m.content)])
                for m in messages
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Normalise the two response shapes into plain text.

        VERIFY-D1: exercise both branches against the live endpoint.
        """
        result = getattr(response, "data", response)
        chat_response = getattr(result, "chat_response", None)
        if chat_response is None:
            return str(result)

        # Cohere family: a flat .text
        text = getattr(chat_response, "text", None)
        if text:
            return text

        # Generic family: choices[0].message.content[0].text
        choices = getattr(chat_response, "choices", None) or []
        if choices:
            content = getattr(getattr(choices[0], "message", None), "content", None) or []
            parts = [getattr(part, "text", "") for part in content]
            joined = "".join(p for p in parts if p)
            if joined:
                return joined

        return ""

    @staticmethod
    def _extract_usage(response: Any) -> tuple[int, int, bool]:
        """Return ``(tokens_in, tokens_out, provider_reported)``."""
        result = getattr(response, "data", response)
        chat_response = getattr(result, "chat_response", None)
        usage = getattr(chat_response, "usage", None) if chat_response else None
        if usage is None:
            return 0, 0, False
        tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        tokens_out = getattr(usage, "completion_tokens", 0) or 0
        return int(tokens_in), int(tokens_out), True

    # -- embeddings -------------------------------------------------------
    def embed(self, texts: list[str], *, input_type: str = "document") -> EmbedResult:
        from oci.generative_ai_inference.models import EmbedTextDetails  # noqa: PLC0415

        # Cohere embed models project documents and queries into different
        # spaces; passing the wrong one degrades retrieval silently.
        oci_input_type = (
            EmbedTextDetails.INPUT_TYPE_SEARCH_QUERY
            if input_type == "query"
            else EmbedTextDetails.INPUT_TYPE_SEARCH_DOCUMENT
        )

        details = EmbedTextDetails(
            inputs=texts,
            serving_mode=self._serving(self._embed_model),
            compartment_id=self._compartment_id,
            input_type=oci_input_type,
            truncate="END",
        )

        try:
            response = self._client.embed_text(details)
        except Exception as exc:
            raise ProviderUnavailableError(f"OCI Generative AI embed failed: {exc}") from exc

        vectors = list(getattr(response.data, "embeddings", []) or [])
        dim = len(vectors[0]) if vectors else self._dim

        if vectors and dim != self._dim:
            # A dimension mismatch corrupts the pgvector column silently. Fail
            # loudly instead: EMBEDDING_DIM and the model must agree.
            raise ProviderConfigurationError(
                f"EMBEDDING_DIM={self._dim} but {self._embed_model} returned {dim}-dim "
                "vectors. Fix EMBEDDING_DIM and the vector column together, then "
                "re-index - mixed dimensions cannot be searched."
            )

        return EmbedResult(
            vectors=vectors,
            dim=dim,
            model=self._embed_model,
            tokens_in=sum(estimate_tokens(t) for t in texts),
            estimated=True,  # embed_text does not report token usage
        )

    # -- readiness --------------------------------------------------------
    def probe(self) -> bool:
        """List models on the control plane - cheap, and not a billable call."""
        try:
            self._get_control_client().list_models(
                compartment_id=self._compartment_id, limit=1
            )
            return True
        except Exception as exc:
            logger.warning(
                "provider_probe_failed",
                extra={"provider": self.name, "region": self._region, "error": str(exc)},
            )
            return False
