import type { ReactNode } from "react";
import { Button } from "./Button";
import { Modal } from "./Modal";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Konfirmo",
                                danger = false, loading = false,
                                onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onCancel} title={title}
           footer={
             <>
               <Button variant="outline" onClick={onCancel} disabled={loading}>Anulo</Button>
               <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}
                       loading={loading}>
                 {confirmLabel}
               </Button>
             </>
           }>
      <div className="text-sm text-slate-600 dark:text-slate-300">{message}</div>
    </Modal>
  );
}
