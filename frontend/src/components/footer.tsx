import { Link } from "react-router-dom";
import { Brain, Code2, Network } from "lucide-react";
import { Logo } from "@/components/logo";

function FooterLogo() {
  return <Logo inverted />;
}

export default function FooterSection() {
  return (
    <>
      <section className="bg-white px-6 py-10">
        <div className="relative mx-auto max-w-7xl overflow-hidden rounded-2xl bg-primary px-8 py-8 text-primary-foreground shadow-xl shadow-primary/20">
          <div className="absolute -left-8 -bottom-8 h-32 w-32 rounded-full border-[18px] border-white/10" />
          <div className="absolute -right-4 -top-4 grid grid-cols-4 gap-2 opacity-30">
            {Array.from({ length: 24 }).map((_, index) => (
              <span key={index} className="h-1.5 w-1.5 rounded-full bg-white" />
            ))}
          </div>
          <div className="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-extrabold">
                Mulai Eksplorasi Penelitian Sekarang
              </h2>
              <p className="mt-2 text-primary-foreground/80">
                Temukan, pahami, dan hubungkan penelitian dengan baik.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/login"
                className="rounded-lg bg-white px-8 py-3 font-bold text-primary transition hover:bg-white/90"
              >
                Mulai Sekarang
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer id="tentang" className="bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-[1.4fr_0.8fr_0.8fr_1fr]">
          <div>
            <FooterLogo />
            <p className="mt-4 max-w-xs text-sm leading-6 text-slate-300">
              Eksplorasi penelitian untuk analisis paper yang lebih baik.
            </p>
          </div>

          <div>
            <h3 className="font-extrabold">Navigasi</h3>
            <div className="mt-4 grid gap-2 text-sm text-slate-300">
              <a href="#beranda">Beranda</a>
              <a href="#fitur">Alur kerja</a>
              <a href="#tentang">Tentang</a>
            </div>
          </div>

          <div>
            <h3 className="font-extrabold">Sumber Data</h3>
            <div className="mt-4 grid gap-2 text-sm text-slate-300">
              <span>Google Scholar</span>
            </div>
          </div>

          <div>
            <h3 className="font-extrabold">Kontak</h3>
            <p className="mt-4 text-sm text-slate-300">
              papercipoliwangi@gmail.com
            </p>
            <div className="mt-4 flex gap-4 text-slate-300">
              <Code2 className="h-5 w-5" />
              <Brain className="h-5 w-5" />
              <Network className="h-5 w-5" />
            </div>
            <p className="mt-8 text-sm text-slate-400">
              (c) 2026 PaperCitation. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </>
  );
}
