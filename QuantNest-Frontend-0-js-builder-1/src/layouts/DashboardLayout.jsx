import { Outlet } from "react-router-dom";
import { useSidebar } from "@/contexts/sidebar-context";
import { usePageTitle } from "@/hooks/use-page-title";
import Sidebar from "@/components/dashboard/sidebar";
import MainContentHeader from "@/components/dashboard/main-content-header";

export default function DashboardLayout() {
  const { isOpen } = useSidebar();
  const { title, subtitle } = usePageTitle();

  return (
    <div className="flex min-h-screen bg-black">
      <Sidebar />
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          isOpen ? "ml-64 sm:ml-72 lg:ml-64" : "ml-0"
        }`}
      >
        <MainContentHeader title={title} subtitle={subtitle} />
        <main className="flex-1 overflow-auto scrollbar-custom">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
