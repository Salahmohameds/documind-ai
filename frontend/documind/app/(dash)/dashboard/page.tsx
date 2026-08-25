import type { Metadata } from "next";
import { DashboardView } from "./dashboard-view";

export const metadata: Metadata = { title: "Dashboard · DocuMind AI" };

export default function DashboardPage() {
  return <DashboardView />;
}
