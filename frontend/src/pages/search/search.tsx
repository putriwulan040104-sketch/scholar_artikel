import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, SlidersHorizontal } from "lucide-react";

export function Searchpage() {
  return (
    <div className="flex items-center justify-center">
      <Card className="w-full max-w-4xl shadow-md rounded-xl">
        <section className="mx-auto max-w-6xl px-8 py-10">
          <div className="text-center">
            <h1 className="md:text-xl text-3xl font-bold leading-tight">
              Hai, <span className="text-black font-bold">User</span>
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-md text-slate-500">
              Mau cari publikasi apa hari ini?
            </p>
          </div>

          <div className="mx-auto mt-10 flex max-w-4xl items-center gap-2 rounded-3xl border bg-white p-2 shadow-sm">
            <Search className="h-5 w-5 ml-2 text-slate-400" />

            <input
              type="text"
              placeholder="Cari artikel, topik, atau keyword..."
              className="flex-1 border-none bg-transparent outline-none"
            />

            <Dialog>
              <DialogTrigger asChild>
                <button className="hover:bg-black/8 rounded-xl py-2 px-2">
                  <SlidersHorizontal className="w-4 h-4" />
                </button>
              </DialogTrigger>

              <DialogContent className="max-w-xl min-h-[350px] rounded-2xl border border-black shadow-md">
                <DialogHeader>
                  <DialogTitle className="text-center">
                    Pencarian Publikasi
                  </DialogTitle>
                </DialogHeader>

                <div className="space-y-8 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    {/* Jenis Artikel */}
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">
                        Jenis artikel
                      </label>

                      <Select>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Jenis artikel" />
                        </SelectTrigger>

                        <SelectContent>
                          <SelectItem value="open">
                            Open Source
                          </SelectItem>

                          <SelectItem value="close">
                            Close Source
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Tahun */}
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">
                        Tahun terbit
                      </label>

                      <div className="flex gap-2">
                        <Select>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="awal" />
                          </SelectTrigger>

                          <SelectContent>
                            {Array.from({ length: 6 }, (_, i) => {
                              const year = 2021 + i;

                              return (
                                <SelectItem
                                  key={year}
                                  value={year.toString()}
                                >
                                  {year}
                                </SelectItem>
                              );
                            })}
                          </SelectContent>
                        </Select>

                        <Select>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="akhir" />
                          </SelectTrigger>

                          <SelectContent>
                            {Array.from({ length: 6 }, (_, i) => {
                              const year = 2021 + i;

                              return (
                                <SelectItem
                                  key={year}
                                  value={year.toString()}
                                >
                                  {year}
                                </SelectItem>
                              );
                            })}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Analisis */}
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">
                        Jenis analisis
                      </label>

                      <Select>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Co-citation" />
                        </SelectTrigger>

                        <SelectContent>
                          <SelectItem value="co">
                            Co-citation
                          </SelectItem>

                          <SelectItem value="bib">
                            Bibliographic
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Jumlah */}
                    <div className="flex flex-col gap-2">
                      <label className="text-sm">
                        Jumlah kemunculan
                      </label>

                      <Input
                        type="number"
                        placeholder="0"
                      />
                    </div>
                  </div>

                  <div className="flex justify-center mt-16">
                    <Button className="px-16">
                      Terapkan Filter
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <button className="rounded-xl bg-gradient-to-r from-indigo-500 to-blue-500 px-5 py-2 font-medium text-white transition hover:opacity-90">
              Cari
            </button>
          </div>

          {/* TAGS */}
          {/* <p className="mx-auto mt-8 max-w-2xl text-md text-slate-500">
            Coba pencarian lain
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            {[
              "Citation network machine learning",
              "Bibliometric analysis",
              "Information retrieval 2023-2026",
              "Web scraping Google Scholar",
            ].map((item) => (
              <button
                key={item}
                className="rounded-full border bg-white px-5 py-2 text-sm text-slate-600 transition hover:border-indigo-400 hover:text-indigo-600"
              >
                {item}
              </button>
            ))}
          </div> */}
        </section>
      </Card>
    </div>
  );
}
