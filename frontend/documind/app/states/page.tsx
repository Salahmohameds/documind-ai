import type { Metadata } from "next";
import { StatesView } from "./states-view";

export const metadata: Metadata = { title: "States & responsive · DocuMind AI" };

export default function StatesPage() {
  return <StatesView />;
}
