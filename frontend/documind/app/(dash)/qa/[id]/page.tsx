import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { DOCUMENTS } from "@/lib/mock/data";
import { QaView } from "./qa-view";

export async function generateMetadata({ params }: PageProps<"/qa/[id]">): Promise<Metadata> {
  const { id } = await params;
  const doc = DOCUMENTS.find((d) => d.id === id);
  return { title: `Ask ${doc?.name ?? "document"} · DocuMind AI` };
}

export default async function DocumentQaPage({ params }: PageProps<"/qa/[id]">) {
  const { id } = await params;
  const doc = DOCUMENTS.find((d) => d.id === id);
  if (!doc) notFound();

  return <QaView docId={doc.id} docName={doc.name} totalPages={doc.pages} />;
}
