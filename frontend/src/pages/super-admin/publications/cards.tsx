import { BookOpen, CircleAlert, CircleCheck } from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface PublicationStatCardsProps {
  total: number;
  complete: number;
  partial: number;
  withoutReferences: number;
}

const cards = [
  { key: "total", label: "Total Publikasi", icon: BookOpen },
  { key: "complete", label: "Data Lengkap", icon: CircleCheck },
  { key: "partial", label: "Data Sebagian", icon: CircleAlert },
] as const;

export function PublicationStatCards(props: PublicationStatCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {cards.map(({ key, label, icon: Icon }) => (
        <Card key={key}>
          <CardHeader className="flex flex-row items-center justify-between gap-3 p-4 sm:p-6">
            <div>
              <CardDescription>{label}</CardDescription>
              <CardTitle className="mt-1 text-2xl sm:text-3xl">
                {props[key]}
              </CardTitle>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}
