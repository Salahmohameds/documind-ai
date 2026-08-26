import type { Metadata } from "next";
import { fetchDocument } from "@/lib/server/documents";
import { DocumentDetailView } from "./detail-view";

export async function generateMetadata({
  params,
}: PageProps<"/documents/[id]">): Promise<Metadata> {
  const { id } = await params;
  const doc = await fetchDocument(id);
  return { title: `${doc?.name ?? "Document"} · DocuMind AI` };
}

export default async function DocumentDetailPage({ params }: PageProps<"/documents/[id]">) {
  const { id } = await params;
  // The view loads the document itself so it owns its loading / error states —
  // including documents created in this session, which no static param covers.
  return <DocumentDetailView id={id} />;
}
