import { Card } from "@/components/ui/card";

export default function Features() {
  return (
    <section className="bg-background @container py-6">
      <div className="mx-auto max-w-5xl px-4">
        <div className="text-center">
          <h2 className="text-balance font-serif text-4xl font-medium">
            Kenapa PaperCi?
          </h2>
          <p className="text-muted-foreground mt-4 text-balance">
            Everything you need to build, connect, and scale your integrations
            effortlessly.
          </p>
        </div>
        <div className="@lg:grid-cols-5 mt-8 grid gap-3 *:p-2">
          <Card variant="mixed" className="row-span-2 grid grid-rows-subgrid">
            <div className="space-y-2">
              <h3 className="text-foreground font-medium">
                Pencarian yang Relevan
              </h3>
              <p className="text-muted-foreground text-sm">
                Algoritma yang membantu menemukan artikel paling relevan.
              </p>
            </div>
          </Card>
          <Card
            variant="mixed"
            className="row-span-2 grid grid-rows-subgrid overflow-hidden"
          >
            <div className="space-y-2">
              <h3 className="text-foreground font-medium">Relasi Penelitian Terlihat</h3>
              <p className="text-muted-foreground text-sm">
                Citation Network yang memvisualisasikan hubungan antar penelitian.
              </p>
            </div>
          </Card>
          <Card
            variant="mixed"
            className="row-span-2 grid grid-rows-subgrid overflow-hidden"
          >
            <div className="space-y-2">
              <h3 className="text-foreground font-medium">Analisis Lebih Cepat</h3>
              <p className="text-muted-foreground mt-2 text-sm">
                Filter dan visualisasi membantu memahami tren penelitian.
              </p>
            </div>
          </Card>
          <Card variant="mixed" className="row-span-2 grid grid-rows-subgrid">
            <div className="space-y-2">
              <h3 className="font-medium">Kelola Referensi Mudah</h3>
              <p className="text-muted-foreground text-sm">
                Simpan artikel favorit dan akses kembali kapan saja dengan mudah.
              </p>
            </div>
          </Card>
          <Card variant="mixed" className="row-span-2 grid grid-rows-subgrid">
            <div className="space-y-2">
              <h3 className="font-medium">Dukung Keputusan Riset</h3>
              <p className="text-muted-foreground text-sm">
                Temukan topik potensial dan paper penting untuk penelitian.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}
