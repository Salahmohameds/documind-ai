import { Sidebar } from "@/components/shell/sidebar";
import { SidebarProvider } from "@/components/shell/sidebar-state";
import { Topbar } from "@/components/shell/topbar";

export default function DashLayout({ children }: LayoutProps<"/">) {
  return (
    <SidebarProvider>
      <div
        style={{
          width: "100%",
          // dvh so mobile browser chrome doesn't clip the last row.
          height: "100dvh",
          display: "flex",
          background: "var(--canvas)",
          overflow: "hidden",
        }}
      >
        <Sidebar />
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <Topbar />
          {children}
        </div>
      </div>
    </SidebarProvider>
  );
}
