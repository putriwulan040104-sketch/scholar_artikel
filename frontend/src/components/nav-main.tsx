import { Collapsible, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { GalleryVerticalEnd } from "lucide-react";
import { Link } from "react-router-dom";

export function NavMain({
  items,
}: {
  items: {
    title: string;
    url: string;
    icon?: React.ReactNode;
    disabled?: boolean;
    items?: {
      title: string;
      url: string;
    }[];
  }[];
}) {
  return (
    <>
      <SidebarMenu className="bg-primary py-5 px-4">
        <SidebarMenuItem className="mr-4">
          <a href="/search" className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center -ml-1">
              <GalleryVerticalEnd className="size-6 text-white" />
            </div>
            <div className="flex flex-colleading-none">
              <span className="text-white text-lg font-semibold">PaperCitation</span>
            </div>
          </a>
        </SidebarMenuItem>
      </SidebarMenu>
      <SidebarMenu className="gap-2 px-2 py-4">
        {items.map((item) => (
          <Collapsible key={item.title} asChild className="group/collapsible">
            <SidebarMenuItem>
              <CollapsibleTrigger asChild>
                <SidebarMenuButton
                  tooltip={item.disabled ? `${item.title} (lakukan pencarian dulu)` : item.title}
                  className="flex items-center gap-3 text-base py-2 pl-4"
                  disabled={item.disabled}
                >
                  {item.disabled ? (
                    <div
                      aria-disabled="true"
                      className="flex w-full cursor-not-allowed items-center gap-3 opacity-50"
                    >
                      <div className="flex h-5 w-5 items-center justify-center [&_svg]:h-4 [&_svg]:w-4">
                        {item.icon}
                      </div>
                      <span>{item.title}</span>
                    </div>
                  ) : (
                    <Link to={item.url} className="flex items-center gap-3 w-full">
                      <div className="flex h-5 w-5 items-center justify-center [&_svg]:h-4 [&_svg]:w-4">
                        {item.icon}
                      </div>
                      <span>{item.title}</span>
                    </Link>
                  )}
                </SidebarMenuButton>
              </CollapsibleTrigger>
            </SidebarMenuItem>
          </Collapsible>
        ))}
      </SidebarMenu>
    </>
  );
}
