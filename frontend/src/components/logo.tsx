import { cn } from "@/lib/utils";
import logoSymbol from "@/assets/paperci-logo-symbol.svg";

export const Logo = ({
  className,
  inverted = false,
}: {
  className?: string;
  uniColor?: boolean;
  inverted?: boolean;
}) => {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <img
        src={logoSymbol}
        alt="PaperCitation logo"
        className="h-9 w-12 object-contain"
      />
      <span
        className={cn(
          "text-xl font-extrabold leading-none",
          inverted ? "text-white" : "text-slate-950",
        )}
      >
        PaperCitation
      </span>
    </div>
  );
};

export const LogoIcon = ({
  className,
}: {
  className?: string;
  uniColor?: boolean;
}) => {
  return (
    <img
      src={logoSymbol}
      alt="PaperCitation logo"
      className={cn("h-8 w-10 object-contain", className)}
    />
  );
};
