import * as React from "react"
import { useNavigate } from "react-router-dom";
import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core"
import { restrictToVerticalAxis } from "@dnd-kit/modifiers"
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnFiltersState,
  type Row,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"
import { z } from "zod"

import { useIsMobile } from "@/hooks/use-mobile"
// import { Badge } from "@/components/ui/badge"                        // ← dihapus: tidak dipakai setelah Tabs dihapus
import { Button } from "@/components/ui/button"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
// import {                                                              // ← dihapus: Columns button dihapus
//   DropdownMenu,
//   DropdownMenuCheckboxItem,
//   DropdownMenuContent,
//   DropdownMenuTrigger,
// } from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
// import {                                                              // ← dihapus: Tabs dihapus
//   Tabs,
//   TabsContent,
//   TabsList,
//   TabsTrigger,
// } from "@/components/ui/tabs"
import {
  GripVerticalIcon,
  // Columns3Icon,                                                      // ← dihapus: Columns button dihapus
  // ChevronDownIcon,                                                    // ← dihapus: Columns button dihapus
  // PlusIcon,                                                           // ← dihapus: Add Section diganti Jaringan Sitasi
  ChevronsLeftIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsRightIcon,
  TrendingUpIcon,
  Star,
  FileText,
  ExternalLink,
  Network,                                                               // ← baru: icon Jaringan Sitasi
} from "lucide-react"

// ─── Schema ────────────────────────────────────────────────────────────────────
// ✅ BENAR — gunakan .optional() untuk field opsional
export const schema = z.object({
  id              : z.number(),
  rank            : z.number(),
  title           : z.string(),
  authors         : z.string(),
  year            : z.number().optional(),
  source          : z.string().optional(),
  category        : z.string().optional(),
  abstract        : z.string().optional(),
  similarity_score: z.number(),
  pdf_url         : z.string().nullable().optional(),
  url             : z.string().nullable().optional(),
  access_url      : z.string().nullable().optional(),
  is_pdf          : z.union([z.boolean(), z.string()]).optional(),
  scrape_status   : z.string().optional(),
  favorite        : z.boolean().default(false),   // ← bukan favorite?: boolean
})

// ─── Helper: cek apakah URL valid ──────────────────────────────────────────────
function isValidUrl(url?: string | null): boolean {
  if (!url) return false
  const trimmed = url.trim()
  return (
    trimmed !== "" &&
    trimmed !== "nan" &&
    trimmed !== "None" &&
    trimmed !== "null" &&
    trimmed.startsWith("http")
  )
}

// ─── Helper: cek apakah link langsung ke PDF ──────────────────────────────────
function isPdfLink(url: string, isPdf?: boolean | string): boolean {
  // is_pdf dari CSV bisa berupa string "True"
  if (isPdf === true || isPdf === "True") return true
  return url.toLowerCase().endsWith(".pdf") || url.toLowerCase().includes(".pdf")
}

// ─── DragHandle ────────────────────────────────────────────────────────────────
function DragHandle({ id }: { id: number }) {
  const { attributes, listeners } = useSortable({ id })
  return (
    <Button
      {...attributes}
      {...listeners}
      variant="ghost"
      size="icon"
      className="size-7 text-muted-foreground hover:bg-transparent"
    >
      <GripVerticalIcon className="size-3 text-muted-foreground" />
      <span className="sr-only">Drag to reorder</span>
    </Button>
  )
}

// ─── Columns ───────────────────────────────────────────────────────────────────
const columns: ColumnDef<z.infer<typeof schema>>[] = [
  {
    id: "drag",
    header: () => null,
    cell: ({ row }) => <DragHandle id={row.original.id} />,
  },
  {
    accessorKey: "rank",
    header: "Rank",
    cell: ({ row }) => (
      <div className="font-bold text-slate-700 w-8 text-center">
        {row.original.rank}
      </div>
    ),
  },
  {
    accessorKey: "title",
    header: "Judul Artikel",
    cell: ({ row }) => <TableCellViewer item={row.original} />,
    enableHiding: false,
  },
  {
    accessorKey: "authors",
    header: "Penulis",
    cell: ({ row }) => (
      <div className="text-slate-500 max-w-[200px] truncate text-sm">
        {row.original.authors}
      </div>
    ),
  },
  {
    accessorKey: "similarity_score",
    header: "Similarity",
    cell: ({ row }) => (
      <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-semibold">
        {row.original.similarity_score.toFixed(4)}
      </span>
    ),
  },
  {
    id: "akses",
    header: "Akses",
    cell: ({ row }) => {
      const { pdf_url, url, access_url, is_pdf } = row.original

      // Prioritas: access_url → pdf_url → url
      const pdfCandidate = isValidUrl(access_url)
        ? access_url!
        : isValidUrl(pdf_url)
        ? pdf_url!
        : null

      const articleUrl = isValidUrl(url) ? url! : null

      // Jika ada URL yang merupakan PDF langsung → tampilkan Download PDF
      if (pdfCandidate && isPdfLink(pdfCandidate, is_pdf)) {
        return (
          <a
            href={pdfCandidate}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-green-600 font-medium hover:text-green-800 hover:underline transition-colors"
          >
            <FileText className="h-3.5 w-3.5" />
            Download PDF
          </a>
        )
      }

      // Jika tidak ada PDF tapi ada URL artikel → tampilkan Lihat Artikel
      if (articleUrl) {
        return (
          <a
            href={articleUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 hover:underline transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Lihat Artikel
          </a>
        )
      }

      // Jika pdfCandidate ada tapi bukan PDF (misal halaman web berbayar) → Lihat Artikel
      if (pdfCandidate) {
        return (
          <a
            href={pdfCandidate}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 hover:underline transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Lihat Artikel
          </a>
        )
      }

      return <span className="text-slate-400 text-xs">Tidak tersedia</span>
    },
  },
  {
  id: "favorite",
  header: "Favorit",
  cell: ({ row }) => {
    // ── Cek apakah sudah ada di localStorage saat render ──
    const isAlreadyFavorite = (): boolean => {
      try {
        const existing = JSON.parse(localStorage.getItem("favorites") || "[]")
        return existing.some((item: { id: number }) => item.id === row.original.id)
      } catch (_) {
        return false
      }
    }

    const [favorite, setFavorite] = React.useState(() => 
      row.original.favorite || isAlreadyFavorite()
    )

    const toggleFavorite = () => {
      const updated = !favorite
      setFavorite(updated)

      try {
        const existing: z.infer<typeof schema>[] = JSON.parse(
          localStorage.getItem("favorites") || "[]"
        )

        if (updated) {
          // ── Tolak duplikat: cek id dulu sebelum push ──
          const alreadyExists = existing.some((item) => item.id === row.original.id)
          if (!alreadyExists) {
            localStorage.setItem(
              "favorites",
              JSON.stringify([...existing, row.original])
            )
          }
        } else {
          localStorage.setItem(
            "favorites",
            JSON.stringify(existing.filter((item) => item.id !== row.original.id))
          )
        }
      } catch (_) {}
    }

    return (
      <button onClick={toggleFavorite} className="flex items-center justify-center">
        <Star
          className={`h-5 w-5 transition-colors ${
            favorite
              ? "fill-yellow-400 text-yellow-400"
              : "text-slate-300 hover:text-slate-400"
          }`}
        />
      </button>
    )
  },
},
]

// ─── DraggableRow ──────────────────────────────────────────────────────────────
function DraggableRow({ row }: { row: Row<z.infer<typeof schema>> }) {
  const { transform, transition, setNodeRef, isDragging } = useSortable({
    id: row.original.id,
  })
  return (
    <TableRow
      data-state={row.getIsSelected() && "selected"}
      data-dragging={isDragging}
      ref={setNodeRef}
      className="relative z-0 data-[dragging=true]:z-10 data-[dragging=true]:opacity-80"
      style={{
        transform: CSS.Transform.toString(transform),
        transition: transition,
      }}
    >
      {row.getVisibleCells().map((cell) => (
        <TableCell key={cell.id}>
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </TableCell>
      ))}
    </TableRow>
  )
}

// ─── DataTable ─────────────────────────────────────────────────────────────────
export function DataTable({
  data: initialData,
}: {
  data: z.infer<typeof schema>[]
}) {
  const [data, setData] = React.useState(() => initialData)
  const [rowSelection, setRowSelection]         = React.useState({})
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [columnFilters, setColumnFilters]       = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting]                   = React.useState<SortingState>([])
  const [pagination, setPagination]             = React.useState({ pageIndex: 0, pageSize: 10 })

  React.useEffect(() => {
    setData(initialData)
    setPagination((prev) => ({ ...prev, pageIndex: 0 }))
    setRowSelection({})
  }, [initialData])
  
  const sortableId = React.useId()
  const sensors = useSensors(
    useSensor(MouseSensor, {}),
    useSensor(TouchSensor, {}),
    useSensor(KeyboardSensor, {})
  )

  const dataIds = React.useMemo<UniqueIdentifier[]>(
    () => data?.map(({ id }) => id) || [],
    [data]
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility, rowSelection, columnFilters, pagination },
    getRowId: (row) => row.id.toString(),
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (active && over && active.id !== over.id) {
      setData((data) => {
        const oldIndex = dataIds.indexOf(active.id)
        const newIndex = dataIds.indexOf(over.id)
        return arrayMove(data, oldIndex, newIndex)
      })
    }
  }

  return (
    // ── SEBELUM: pakai <Tabs> wrapper ──────────────────────────────────────────
    // <Tabs defaultValue="outline" className="w-full flex-col justify-start gap-6">
    // ── SESUDAH: ganti dengan <div> biasa ─────────────────────────────────────
    <div className="w-full flex flex-col gap-6">

      {/* ── SEBELUM: ada Select view + TabsList + Columns button + Add Section ──
      <div className="flex items-center justify-between px-4 lg:px-6">
        <Label htmlFor="view-selector" className="sr-only">View</Label>
        <Select defaultValue="outline">
          <SelectTrigger className="flex w-fit @4xl/main:hidden" size="sm" id="view-selector">
            <SelectValue placeholder="Select a view" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="outline">Outline</SelectItem>
              <SelectItem value="past-performance">Past Performance</SelectItem>
              <SelectItem value="key-personnel">Key Personnel</SelectItem>
              <SelectItem value="focus-documents">Focus Documents</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>

        <TabsList className="hidden **:data-[slot=badge]:size-5 **:data-[slot=badge]:rounded-full **:data-[slot=badge]:bg-muted-foreground/30 **:data-[slot=badge]:px-1 @4xl/main:flex">
          <TabsTrigger value="outline">Outline</TabsTrigger>
          <TabsTrigger value="past-performance">
            Past Performance <Badge variant="secondary">3</Badge>
          </TabsTrigger>
          <TabsTrigger value="key-personnel">
            Key Personnel <Badge variant="secondary">2</Badge>
          </TabsTrigger>
          <TabsTrigger value="focus-documents">Focus Documents</TabsTrigger>
        </TabsList>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Columns3Icon data-icon="inline-start" />
                Columns
                <ChevronDownIcon data-icon="inline-end" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-32">
              {table
                .getAllColumns()
                .filter((col) => typeof col.accessorFn !== "undefined" && col.getCanHide())
                .map((col) => (
                  <DropdownMenuCheckboxItem
                    key={col.id}
                    className="capitalize"
                    checked={col.getIsVisible()}
                    onCheckedChange={(value) => col.toggleVisibility(!!value)}
                  >
                    {col.id}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" size="sm">
            <PlusIcon />
            <span className="hidden lg:inline">Add Section</span>
          </Button>
        </div>
      </div>
      ── AKHIR SEBELUM ── */}

      {/* ── SESUDAH: hanya tombol Jaringan Sitasi di kanan ── */}
      <div className="flex items-center justify-end px-4 lg:px-6">
        <Button variant="outline" size="sm">
          <Network className="h-4 w-4" />
          <span>Jaringan Sitasi</span>
        </Button>
      </div>

      {/* ── SEBELUM: pakai <TabsContent value="outline"> ──────────────────────
      <TabsContent
        value="outline"
        className="relative flex flex-col gap-4 overflow-auto px-4 lg:px-6"
      >
      ── SESUDAH: ganti dengan <div> biasa ── */}
      <div className="relative flex flex-col gap-4 overflow-auto px-4 lg:px-6">

        <div className="overflow-hidden rounded-lg border">
          <DndContext
            collisionDetection={closestCenter}
            modifiers={[restrictToVerticalAxis]}
            onDragEnd={handleDragEnd}
            sensors={sensors}
            id={sortableId}
          >
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-muted">
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id} colSpan={header.colSpan}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody className="**:data-[slot=table-cell]:first:w-8">
                {table.getRowModel().rows?.length ? (
                  <SortableContext items={dataIds} strategy={verticalListSortingStrategy}>
                    {table.getRowModel().rows.map((row) => (
                      <DraggableRow key={row.id} row={row} />
                    ))}
                  </SortableContext>
                ) : (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      No results.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </DndContext>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4">
          <div className="hidden flex-1 text-sm text-muted-foreground lg:flex">
            {table.getFilteredSelectedRowModel().rows.length} of{" "}
            {table.getFilteredRowModel().rows.length} row(s) selected.
          </div>
          <div className="flex w-full items-center gap-8 lg:w-fit">
            <div className="hidden items-center gap-2 lg:flex">
              <Label htmlFor="rows-per-page" className="text-sm font-medium">
                Rows per page
              </Label>
              <Select
                value={`${table.getState().pagination.pageSize}`}
                onValueChange={(value) => table.setPageSize(Number(value))}
              >
                <SelectTrigger size="sm" className="w-20" id="rows-per-page">
                  <SelectValue placeholder={table.getState().pagination.pageSize} />
                </SelectTrigger>
                <SelectContent side="top">
                  <SelectGroup>
                    {[10, 20, 30, 40, 50].map((pageSize) => (
                      <SelectItem key={pageSize} value={`${pageSize}`}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="flex w-fit items-center justify-center text-sm font-medium">
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </div>
            <div className="ml-auto flex items-center gap-2 lg:ml-0">
              <Button
                variant="outline"
                className="hidden h-8 w-8 p-0 lg:flex"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">Go to first page</span>
                <ChevronsLeftIcon />
              </Button>
              <Button
                variant="outline"
                className="size-8"
                size="icon"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">Go to previous page</span>
                <ChevronLeftIcon />
              </Button>
              <Button
                variant="outline"
                className="size-8"
                size="icon"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">Go to next page</span>
                <ChevronRightIcon />
              </Button>
              <Button
                variant="outline"
                className="hidden size-8 lg:flex"
                size="icon"
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">Go to last page</span>
                <ChevronsRightIcon />
              </Button>
            </div>
          </div>
        </div>

      {/* </TabsContent> ← SEBELUM penutup TabsContent */}
      </div>

      {/* ── SEBELUM: Tab lain — dikomentari semua ─────────────────────────────
      <TabsContent value="past-performance" className="flex flex-col px-4 lg:px-6">
        <div className="aspect-video w-full flex-1 rounded-lg border border-dashed" />
      </TabsContent>
      <TabsContent value="key-personnel" className="flex flex-col px-4 lg:px-6">
        <div className="aspect-video w-full flex-1 rounded-lg border border-dashed" />
      </TabsContent>
      <TabsContent value="focus-documents" className="flex flex-col px-4 lg:px-6">
        <div className="aspect-video w-full flex-1 rounded-lg border border-dashed" />
      </TabsContent>
      ── AKHIR SEBELUM ── */}

    {/* </Tabs> ← SEBELUM penutup Tabs */}
    </div>
  )
}

// ─── Chart (template asli dipertahankan) ──────────────────────────────────────
const chartData = [
  { month: "January",  desktop: 186, mobile: 80  },
  { month: "February", desktop: 305, mobile: 200 },
  { month: "March",    desktop: 237, mobile: 120 },
  { month: "April",    desktop: 73,  mobile: 190 },
  { month: "May",      desktop: 209, mobile: 130 },
  { month: "June",     desktop: 214, mobile: 140 },
]
const chartConfig = {
  desktop: { label: "Desktop", color: "var(--primary)" },
  mobile:  { label: "Mobile",  color: "var(--primary)" },
} satisfies ChartConfig

// ─── TableCellViewer (drawer detail artikel) ───────────────────────────────────
function TableCellViewer({ item }: { item: z.infer<typeof schema> }) {
  const isMobile = useIsMobile()
  const navigate = useNavigate();
  // Tentukan URL akses terbaik
  const pdfCandidate = isValidUrl(item.access_url)
    ? item.access_url!
    : isValidUrl(item.pdf_url)
    ? item.pdf_url!
    : null

  const hasPdf = pdfCandidate !== null && isPdfLink(pdfCandidate, item.is_pdf)
  const articleUrl = isValidUrl(item.url) ? item.url! : null

  return (
    <Drawer direction={isMobile ? "bottom" : "right"}>
      <DrawerTrigger asChild>
        <Button
      variant="link"
      className="w-fit px-0 text-left text-foreground leading-snug"
      onClick={() => navigate(`/detail/${item.id}`)}
    >
      <span className="line-clamp-2 max-w-[350px] text-sm font-medium">
        {item.title}
      </span>
    </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader className="gap-1">
          <DrawerTitle className="leading-snug">{item.title}</DrawerTitle>
          <DrawerDescription>{item.authors}</DrawerDescription>
        </DrawerHeader>

        <div className="flex flex-col gap-4 overflow-y-auto px-4 text-sm">
          {!isMobile && (
            <>
              <ChartContainer config={chartConfig}>
                <AreaChart accessibilityLayer data={chartData} margin={{ left: 0, right: 10 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tickFormatter={(v) => v.slice(0, 3)}
                    hide
                  />
                  <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="dot" />} />
                  <Area dataKey="mobile"  type="natural" fill="var(--color-mobile)"  fillOpacity={0.6} stroke="var(--color-mobile)"  stackId="a" />
                  <Area dataKey="desktop" type="natural" fill="var(--color-desktop)" fillOpacity={0.4} stroke="var(--color-desktop)" stackId="a" />
                </AreaChart>
              </ChartContainer>
              <Separator />
              <div className="grid gap-2">
                <div className="flex gap-2 leading-none font-medium">
                  Trending up by 5.2% this month <TrendingUpIcon className="size-4" />
                </div>
                <div className="text-muted-foreground">
                  Showing total visitors for the last 6 months.
                </div>
              </div>
              <Separator />
            </>
          )}

          {/* Detail artikel */}
          <div className="grid grid-cols-2 gap-4 py-2">
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Tahun</Label>
              <span>{item.year ?? "-"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Sumber</Label>
              <span className="line-clamp-2">{item.source ?? "-"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Kategori</Label>
              <span>{item.category ?? "-"}</span>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Similarity Score</Label>
              <span className="inline-flex w-fit bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs font-semibold">
                {item.similarity_score.toFixed(4)}
              </span>
            </div>
          </div>

          <Separator />

          {/* Form edit (template asli) */}
          <form className="flex flex-col gap-4">
            <div className="flex flex-col gap-3">
              <Label htmlFor="title">Judul Artikel</Label>
              <Input id="title" defaultValue={item.title} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-3">
                <Label htmlFor="authors">Penulis</Label>
                <Input id="authors" defaultValue={item.authors} />
              </div>
              <div className="flex flex-col gap-3">
                <Label htmlFor="similarity_score">Similarity Score</Label>
                <Input id="similarity_score" defaultValue={item.similarity_score.toString()} />
              </div>
            </div>
          </form>
        </div>

        <DrawerFooter>
          {/* Tombol akses sesuai ketersediaan PDF */}
          {hasPdf ? (
            <a
              href={pdfCandidate!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
            >
              <FileText className="w-4 h-4" />
              Download PDF
            </a>
          ) : articleUrl ? (
            
            <a
              href={articleUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Lihat Artikel
            </a>
          ) : (
            <Button disabled variant="outline">Tidak tersedia</Button>
          )}
          <Button>Submit</Button>
          <DrawerClose asChild>
            <Button variant="outline">Done</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  )
}