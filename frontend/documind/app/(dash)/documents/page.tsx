import type { Metadata } from "next";
import { DocumentsView } from "./documents-view";

export const metadata: Metadata = { title: "Documents · DocuMind AI" };

export default function DocumentsPage() {
  return <DocumentsView />;
}
