import { Sidebar } from "@/components/shell/sidebar";
import { SidebarProvider } from "@/components/shell/sidebar-state";
import { Topbar } from "@/components/shell/topbar";
import { SearchProvider } from "@/components/search/search-provider";

export default function DashLayout({ children }: LayoutProps<"/">) {
  return (
    <SidebarProvider>
      {/* Global search is mounted here rather than in the root layout, so the
          auth pages never load the palette or bind its shortcut. */}
      <SearchProvider>
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
      </SearchProvider>
    </SidebarProvider>
  );
}
