"use client"

import * as React from "react"
import { NavMain } from "@/components/nav-main"
import {
  Sidebar,
  SidebarContent,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Search, Waypoints, Star } from "lucide-react"

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  navMain: [
    {
      title: "Eksplorasi",
      url: "/search",
      icon: (
        <Search
        />
      ),
    },
    {
      title: "Jaringan Sitasi",
      url: "#",
      icon: (
        <Waypoints
        />
      ),
    },
    {
      title: "Artikel Tersimpan",
      url: "/favorite",
      icon: (
        <Star
        />
      ),
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
