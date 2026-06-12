import { Collapsible, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { LogoIcon } from "@/components/logo";
import { Link, useLocation } from "react-router-dom";

export interface NavItem {
  title: string;
  url: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

export function NavMain({ groups }: { groups: NavGroup[] }) {
  const location = useLocation();

  const renderItems = (items: NavItem[]) =>
    items.map((item) => {
      const isActive =
        !item.disabled &&
        (location.pathname === item.url ||
          location.pathname.startsWith(`${item.url}/`));

      return (
        <Collapsible key={item.title} asChild className="group/collapsible">
          <SidebarMenuItem>
            <CollapsibleTrigger asChild>
              <SidebarMenuButton
                tooltip={
                  item.disabled
                    ? `${item.title} (lakukan pencarian dulu)`
                    : item.title
                }
                isActive={isActive}
                className={`flex items-center gap-3 py-2 pl-4 text-base ${
                  isActive
                    ? "bg-primary font-semibold text-primary-foreground hover:bg-primary/70 hover:text-primary-foreground data-active:bg-primary data-active:text-primary-foreground"
                    : ""
                }`}
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
                  <Link to={item.url} className="flex w-full items-center gap-3">
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
      );
    });

  return (
    <>
      <SidebarMenu className="bg-primary px-4 py-5 group-data-[collapsible=icon]:px-2">
        <SidebarMenuItem className="min-w-0">
          <a
            href="/search"
            className="flex min-w-0 items-center gap-3 group-data-[collapsible=icon]:justify-center"
          >
            <div className="flex h-8 w-10 shrink-0 items-center justify-center group-data-[collapsible=icon]:w-8">
              <LogoIcon className="h-8 w-8 brightness-0 invert" />
            </div>
            <div className="min-w-0 group-data-[collapsible=icon]:hidden">
              <span className="truncate text-lg font-semibold text-white">PaperCitation</span>
            </div>
          </a>
        </SidebarMenuItem>
      </SidebarMenu>
      <div className="py-2">
        {groups.map((group, index) => (
          <SidebarGroup key={group.label || `nav-group-${index}`}>
            {group.label ? (
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            ) : null}
            <SidebarGroupContent>
              <SidebarMenu className="gap-2">
                {renderItems(group.items)}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </div>
    </>
  );
}
