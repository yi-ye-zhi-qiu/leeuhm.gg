import Link from "next/link";
import { navItems } from "./NavItems";

export default function NavBar() {
  return (
    <div className="overflow-hidden backdrop-blur-sm fixed w-full flex flex-col items-center justify-center text-sm z-100">
      <div className="w-full sm:w-1/2 md:w-3/4 xl:w-1/2 max-w-full h-12 gap-x-10 justify-between flex p-4 rounded">
        <Link href="/" className="grow text-left">
          leeuhm.gg
        </Link>
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}>
            {item.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
