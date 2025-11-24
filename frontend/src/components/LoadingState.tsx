import { Loader2 } from 'lucide-react';

export default function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="mb-4 h-12 w-12 animate-spin text-primary" />
      <p className="text-lg text-foreground">Đang tìm kiếm sản phẩm tốt nhất cho bạn...</p>
      <p className="mt-2 text-sm text-muted-foreground">
        AI đang phân tích hàng trăm sản phẩm từ Amazon
      </p>
    </div>
  );
}
