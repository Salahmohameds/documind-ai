import type { Metadata } from "next";
import { UploadView } from "./upload-view";

export const metadata: Metadata = { title: "Upload · DocuMind AI" };

export default function UploadPage() {
  return <UploadView />;
}
