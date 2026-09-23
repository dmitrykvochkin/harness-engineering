"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronsUpDown, Radar, Settings } from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import { navItems, type NavItem } from "@/lib/nav";

function isActive(url: string, pathname: string, exact = false) {
  if (url === "/" || exact) return pathname === url;
  return pathname === url || pathname.startsWith(`${url}/`);
}

function sectionOpenForRoute(item: NavItem, pathname: string) {
  if (item.url === "/signals") {
    return isActive(item.url, pathname) || pathname.startsWith("/runs/");
  }
  return isActive(item.url, pathname);
}

function CollapsibleNavItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const openForRoute = sectionOpenForRoute(item, pathname);
  const [open, setOpen] = useState(openForRoute);

  useEffect(() => {
    if (openForRoute) setOpen(true);
  }, [openForRoute, pathname]);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="group/collapsible" asChild>
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton tooltip={item.title}>
            <item.icon />
            <span>{item.title}</span>
            <ChevronsUpDown className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-180" />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarMenuSub>
            {item.subItems?.map((sub) => {
              const subActive = isActive(sub.url, pathname);
              return (
                <SidebarMenuSubItem key={sub.url}>
                  <SidebarMenuSubButton asChild isActive={subActive}>
                    <Link href={sub.url}>
                      {sub.icon && <sub.icon />}
                      <span>{sub.title}</span>
                    </Link>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              );
            })}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  );
}

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Radar className="size-4" />
                </div>
                <div className="grid flex-1 text-left leading-tight">
                  <span className="truncate font-semibold">Harness</span>
                  <span className="truncate text-xs text-muted-foreground">
                    Agent failure detection
                  </span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const active = isActive(item.url, pathname, item.exact);

                if (item.subItems) {
                  return <CollapsibleNavItem key={item.title} item={item} pathname={pathname} />;
                }

                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton tooltip={item.title} isActive={active} asChild>
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="User settings" asChild>
              <Link href="/settings">
                <Settings />
                <span>User settings</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
