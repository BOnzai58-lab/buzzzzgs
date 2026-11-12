interface Props { title: string; message: string; onConfirm: () => void; onCancel: () => void; danger?: boolean }
export default function ConfirmModal({ title, message, onConfirm, onCancel, danger }: Props) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card max-w-sm w-full mx-4">
        <h3 className="text-white font-semibold mb-2">{title}</h3>
        <p className="text-gray-400 text-sm mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
          <button onClick={onConfirm} className={danger ? 'btn-danger' : 'btn-primary'}>Confirm</button>
        </div>
      </div>
    </div>
  )
}

