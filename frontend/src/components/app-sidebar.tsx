"use client"

import * as React from "react"
import { NavMain } from "@/components/nav-main"
import {
  Sidebar,
  SidebarContent,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Search, Waypoints, Star } from "lucide-react"

function hasSearchContext(): boolean {
  try {
    const raw = localStorage.getItem("lastSearchPublicationIds")
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) && parsed.length > 0
  } catch (_error) {
    return false
  }
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [graphEnabled, setGraphEnabled] = React.useState(false)

  React.useEffect(() => {
    const sync = () => setGraphEnabled(hasSearchContext())
    sync()
    window.addEventListener("storage", sync)
    window.addEventListener("search-context-updated", sync)
    return () => {
      window.removeEventListener("storage", sync)
      window.removeEventListener("search-context-updated", sync)
    }
  }, [])

  const navMain = React.useMemo(
    () => [
      {
        title: "Eksplorasi",
        url: "/search",
        icon: <Search />,
      },
      {
        title: "Jaringan Sitasi",
        url: "/citation-graph",
        icon: <Waypoints />,
        disabled: !graphEnabled,
      },
      {
        title: "Artikel Tersimpan",
        url: "/favorite",
        icon: <Star />,
      },
    ],
    [graphEnabled]
  )

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarContent>
        <NavMain items={navMain} />
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
