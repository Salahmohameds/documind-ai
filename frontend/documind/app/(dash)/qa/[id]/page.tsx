import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { fetchDocument } from "@/lib/server/documents";
import { QaView } from "./qa-view";

export async function generateMetadata({ params }: PageProps<"/qa/[id]">): Promise<Metadata> {
  const { id } = await params;
  const doc = await fetchDocument(id);
  return { title: `Ask ${doc?.name ?? "document"} · DocuMind AI` };
}

export default async function DocumentQaPage({ params }: PageProps<"/qa/[id]">) {
  const { id } = await params;
  const doc = await fetchDocument(id);
  if (!doc) notFound();

  return <QaView docId={doc.id} docName={doc.name} totalPages={doc.pages} />;
}
