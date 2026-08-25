import Image from "next/image";

/**
 * The product mark, from `public/docmind-star.svg`. `unoptimized` because the
 * source is already an SVG — running it through the image optimizer would only
 * add a request without shrinking anything.
 */
export function Logo({ size = 30, className }: { size?: number; className?: string }) {
  return (
    <Image
      src="/docmind-star.svg"
      alt=""
      aria-hidden
      width={size}
      height={size}
      priority
      unoptimized
      className={className}
      style={{ width: size, height: size, flex: "none" }}
    />
  );
}

export function Wordmark({ size = 15 }: { size?: number }) {
  return (
    <span
      style={{
        fontSize: size,
        fontWeight: 700,
        letterSpacing: "-.02em",
        color: "var(--text)",
        whiteSpace: "nowrap",
      }}
    >
      DocuMind
    </span>
  );
}
