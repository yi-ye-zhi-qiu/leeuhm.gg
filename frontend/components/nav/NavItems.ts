import type { ComponentType } from "react";

export type NavItem<T extends string = string> = {
  href: T;
  label: string;
};

export const navItems: NavItem<string>[] = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
];
