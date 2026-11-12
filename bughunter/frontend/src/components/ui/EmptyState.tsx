export default function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-gray-600 mb-3">{icon}</div>
      <p className="text-gray-400 font-medium">{title}</p>
      {description && <p className="text-gray-600 text-sm mt-1">{description}</p>}
    </div>
  )
}

