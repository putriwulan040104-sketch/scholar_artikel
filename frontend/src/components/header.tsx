import React from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/logo";

const menuItems = [
  { name: "Beranda", href: "#beranda" },
  { name: "Alur kerja", href: "#demo" },
  { name: "Tentang", href: "#tentang" },
];

function PaperCitationLogo({ className }: { className?: string }) {
  return <Logo className={className} />;
}

export const HeroHeader = () => {
  const [menuState, setMenuState] = React.useState(false);
  const [isScrolled, setIsScrolled] = React.useState(false);

  React.useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 24);
    handleScroll();
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header>
      <nav
        data-state={menuState && "active"}
        className={cn(
          "fixed top-0 z-50 w-full border-b border-transparent bg-white/90 transition-all duration-300",
          isScrolled && "border-slate-100 shadow-sm backdrop-blur",
        )}
      >
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex min-h-[76px] flex-wrap items-center justify-between gap-4">
            <Link to="/" aria-label="PaperCitation beranda">
              <PaperCitationLogo />
            </Link>

            <button
              onClick={() => setMenuState(!menuState)}
              aria-label={menuState ? "Tutup menu" : "Buka menu"}
              className="relative z-20 -mr-2 rounded-md p-2 lg:hidden"
            >
              <Menu className="size-6 data-[state=active]:hidden" />
              <X className={cn("absolute inset-0 m-auto size-6", !menuState && "hidden")} />
            </button>

            <div className="hidden items-center gap-10 text-sm font-semibold text-slate-900 lg:flex">
              {menuItems.map((item, index) => (
                <a
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "border-b-2 border-transparent py-2 transition hover:border-primary hover:text-primary",
                    index === 0 && "border-primary text-primary",
                  )}
                >
                  {item.name}
                </a>
              ))}
            </div>

            <div className="hidden items-center gap-3 lg:flex">
              <Link
                to="/login"
                className="rounded-lg border border-primary px-5 py-2 text-sm font-bold text-primary transition hover:bg-primary/10"
              >
                Masuk
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90"
              >
                Daftar
              </Link>
            </div>

            {menuState && (
              <div className="w-full rounded-2xl border bg-white p-4 shadow-xl lg:hidden">
                <div className="grid gap-2">
                  {menuItems.map((item) => (
                    <a
                      key={item.name}
                      href={item.href}
                      onClick={() => setMenuState(false)}
                      className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-primary/10 hover:text-primary"
                    >
                      {item.name}
                    </a>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <Link
                    to="/login"
                    className="rounded-lg border border-primary px-4 py-2 text-center text-sm font-bold text-primary"
                  >
                    Masuk
                  </Link>
                  <Link
                    to="/register"
                    className="rounded-lg bg-primary px-4 py-2 text-center text-sm font-bold text-primary-foreground"
                  >
                    Daftar
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
};
