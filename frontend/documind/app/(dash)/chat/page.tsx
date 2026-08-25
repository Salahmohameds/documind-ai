import type { Metadata } from "next";
import { ChatView } from "./chat-view";

export const metadata: Metadata = { title: "Ask · DocuMind AI" };

export default function ChatPage() {
  return <ChatView />;
}
