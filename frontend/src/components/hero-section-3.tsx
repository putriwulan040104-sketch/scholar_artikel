import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { HeroHeader } from "./header";
import heroCitationNetwork from "@/assets/hero-citation-network.svg";

function HeroNetwork() {
  return (
    <div className="relative overflow-hidden">
      <img
        src={heroCitationNetwork}
        alt="Ilustrasi citation network PaperCitation"
        className="h-auto w-full object-contain"
        loading="eager"
      />
    </div>
  );
}

export default function HeroSection() {
  return (
    <>
      <HeroHeader />
      <main className="overflow-hidden bg-white">
        <section
          id="beranda"
          className="mx-auto grid max-w-7xl items-center gap-10 px-6 pb-14 pt-32 lg:grid-cols-[0.9fr_1.1fr]"
        >
          <div>
            <h1 className="max-w-2xl text-xl font-extrabold leading-tight tracking-tight text-slate-950 md:text-3xl">
              Temukan Penelitian Secara Baik dengan{" "}
              <span className="text-primary">Citation Network</span>
            </h1>
            <p className="mt-6 max-w-xl text-md leading-8 text-slate-600">
              Sistem Pencarian dengan Sumber Data Google Scholar dalam Membantu
              Menemukan Artikel yang Relavan.
            </p>

            <div className="mt-6 flex flex-wrap gap-4">
              <Link
                to="/login"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2 font-bold text-primary-foreground shadow-lg shadow-primary/20 transition hover:bg-primary/90"
              >
                <Search className="h-5 w-5" />
                Mulai Eksplorasi
              </Link>
            </div>
          </div>
          <HeroNetwork />
        </section>
      </main>
    </>
  );
}
