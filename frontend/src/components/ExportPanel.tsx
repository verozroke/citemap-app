interface Props {
  csvUrl: string
  jsonUrl: string
  onPng: () => void
}

export default function ExportPanel({ csvUrl, jsonUrl, onPng }: Props) {
  return (
    <section className="panel" aria-labelledby="export-title">
      <h2 id="export-title" className="panel__title">
        Export current view
      </h2>
      <div className="button-row">
        <a className="button" href={csvUrl} download>
          Ranking CSV
        </a>
        <a className="button" href={jsonUrl} download>
          Graph JSON
        </a>
        <button type="button" className="button" onClick={onPng}>
          Image PNG
        </button>
      </div>
    </section>
  )
}
