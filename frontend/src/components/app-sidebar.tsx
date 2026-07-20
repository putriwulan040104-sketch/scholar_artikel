"use client";

import * as React from "react";
import { NavMain, type NavItem } from "@/components/nav-main";
import { isSuperAdmin } from "@/api/api";
import { Sidebar, SidebarContent, SidebarRail } from "@/components/ui/sidebar";
import {
  BookOpenText,
  // ClipboardList,
  Home,
  History,
  Search,
  Star,
  UsersRound,
  Waypoints,
  List,
} from "lucide-react";

function hasSearchContext(): boolean {
  try {
    const query = (localStorage.getItem("lastSearchQuery") || "").trim();
    const raw = localStorage.getItem("lastSearchPublicationIds");
    const parsed = raw ? JSON.parse(raw) : [];
    return Boolean(query) && Array.isArray(parsed) && parsed.length > 0;
  } catch {
    return false;
  }
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [graphEnabled, setGraphEnabled] = React.useState(false);
  const [superAdmin, setSuperAdmin] = React.useState(false);

  React.useEffect(() => {
    const sync = () => setGraphEnabled(hasSearchContext());
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("search-context-updated", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("search-context-updated", sync);
    };
  }, []);

  React.useEffect(() => {
    const sync = () => setSuperAdmin(isSuperAdmin());
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("user-updated", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("user-updated", sync);
    };
  }, []);

  const navGroups = React.useMemo(() => {
    const mainItems: NavItem[] = [
      {
        title: "Eksplorasi",
        url: "/search",
        icon: <Search />,
      },
      {
        title: "Jaringan Artikel",
        url: "/citation-graph",
        icon: <Waypoints />,
        disabled: !graphEnabled,
      },
      {
        title: "Daftar Artikel",
        url: "/daftar-artikel",
        icon: <List />,
        disabled: !graphEnabled,
      },
      {
        title: "Artikel Tersimpan",
        url: "/favorite",
        icon: <Star />,
      },
    ];

    if (superAdmin) {
      mainItems.unshift({
        title: "Dashboard",
        url: "/super-admin/dashboard",
        icon: <Home />,
      });

      const adminItems: NavItem[] = [
        {
          title: "Kelola Publikasi",
          url: "/super-admin/publications",
          icon: <BookOpenText />,
        },
        {
          title: "Kelola Pengguna",
          url: "/super-admin/users",
          icon: <UsersRound />,
        },
        // {
        //   title: "Kelola Request",
        //   url: "/super-admin/requests",
        //   icon: <ClipboardList />,
        // },
        {
          title: "Log Aktivitas",
          url: "/super-admin/activity-logs",
          icon: <History />,
        },
      ];

      return [
        { label: "Navigasi Utama", items: mainItems },
        { label: "Administrasi", items: adminItems },
      ];
    }

    return [{ items: mainItems }];
  }, [graphEnabled, superAdmin]);

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarContent>
        <NavMain groups={navGroups} />
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}
