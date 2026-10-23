import { Switch as RadixSwitch } from "radix-ui";
import { useId } from "react";

/** A 36×20 px switch with its label on the right (§4.5). */
export function Switch({
  label,
  checked,
  onCheckedChange,
  disabled = false,
  describedBy,
}: {
  label: string;
  checked: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  describedBy?: string;
}) {
  const id = useId();
  return (
    <div className="flex items-center gap-3">
      <RadixSwitch.Root
        id={id}
        checked={checked}
        disabled={disabled}
        aria-describedby={describedBy}
        data-shape="round"
        className="relative inline-flex h-5 w-9 shrink-0 items-center rounded-round bg-border-control transition-colors duration-(--duration-hover) ease-standard data-[state=checked]:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
        {...(onCheckedChange ? { onCheckedChange } : {})}
      >
        <RadixSwitch.Thumb
          data-shape="round"
          className="block size-4 translate-x-0.5 rounded-round bg-page transition-transform duration-(--duration-hover) ease-standard data-[state=checked]:translate-x-4.5"
        />
      </RadixSwitch.Root>
      <label htmlFor={id} className="text-small font-semibold text-ink">
        {label}
      </label>
    </div>
  );
}
