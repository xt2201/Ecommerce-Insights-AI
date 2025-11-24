import { AlertCircle } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-6">
      <AlertCircle className="mt-0.5 h-6 w-6 flex-shrink-0 text-destructive" />
      <div>
        <h3 className="mb-1 font-semibold text-foreground">Có lỗi xảy ra</h3>
        <p className="text-destructive">{message}</p>
      </div>
    </div>
  );
}
