import type { Metadata } from "next";
import { RegisterView } from "./register-view";

export const metadata: Metadata = { title: "Create your workspace · DocuMind AI" };

export default function RegisterPage() {
  return <RegisterView />;
}
