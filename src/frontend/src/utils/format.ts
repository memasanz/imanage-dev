import type { SearchResultItem, NeutralValue, ConfigField, AgentTraceItem } from '../api/client';

export function neutralText(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  const item = value as NeutralValue;
  return String(item.text ?? item.value ?? item.id ?? '');
}

export function fieldValue(item: SearchResultItem, key: string): string {
  if (key === 'author') return neutralText(item.author);
  if (key === 'title' || key === 'keyword' || key === 'name') return item.name ?? '';
  if (key === 'doctype') return neutralText(item.doctype ?? item.class);
  return neutralText(item.fields?.[key] ?? item[key]);
}

export function formatDate(value?: string) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function formatBytes(value?: number) {
  if (!value) return '—';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function docNumber(item: SearchResultItem) {
  return String(item.doc_num ?? item.document_number ?? item.id.split('!').pop()?.split('.')[0] ?? '—');
}

export function libraryOf(item: SearchResultItem) {
  return String(item.library ?? item.id.split('!')[0] ?? '');
}

export function imanageDeepLink(item: SearchResultItem) {
  const library = libraryOf(item);
  const number = docNumber(item);
  if (!library || number === '—') return undefined;
  return `imanage://open?library=${encodeURIComponent(library)}&document=${encodeURIComponent(number)}`;
}

export function dynamicDetailRows(item: SearchResultItem, configFields: ConfigField[]) {
  return configFields
    .filter((field) => field.show_in_detail)
    .map((field) => ({ label: field.label || field.key, value: neutralText(item.fields?.[field.key]) }))
    .filter((row) => row.value);
}

export function extractTextFromUnknown(payload: unknown): string {
  if (payload == null) return '';
  if (typeof payload === 'string') {
    const trimmed = payload.trim();
    if ((trimmed.startsWith('{') || trimmed.startsWith('[')) && trimmed.length < 1000000) {
      try { return extractTextFromUnknown(JSON.parse(trimmed)); } catch { return payload; }
    }
    return payload;
  }
  if (Array.isArray(payload)) return payload.map(extractTextFromUnknown).filter(Boolean).join('\n');
  if (typeof payload === 'object') {
    const obj = payload as Record<string, unknown>;
    for (const key of ['text', 'content', 'answer']) {
      const found = extractTextFromUnknown(obj[key]);
      if (found) return found;
    }
    if (obj.result) return extractTextFromUnknown(obj.result);
    return Object.values(obj).map(extractTextFromUnknown).filter(Boolean).join('\n');
  }
  return '';
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

export function markdownToSafeHtml(markdown: string) {
  const lines = escapeHtml(markdown).split('\n');
  const html: string[] = [];
  let i = 0;

  const inline = (text: string) => text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|\s)\*([^*]+)\*/g, '$1<em>$2</em>');

  const isTableSep = (line: string) => /^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$/.test(line);
  const isTableRow = (line: string) => line.trim().startsWith('|') && line.includes('|');
  const isTableStart = (idx: number) => isTableRow(lines[idx]) && idx + 1 < lines.length && isTableSep(lines[idx + 1]);
  const isHeading = (line: string) => /^#{1,6}\s+/.test(line);
  const isListItem = (line: string) => /^\s*[-*]\s+/.test(line);
  const splitCells = (line: string) => {
    let value = line.trim();
    if (value.startsWith('|')) value = value.slice(1);
    if (value.endsWith('|')) value = value.slice(0, -1);
    return value.split('|').map((cell) => cell.trim());
  };

  while (i < lines.length) {
    const line = lines[i];

    if (isTableStart(i)) {
      const header = splitCells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) { rows.push(splitCells(lines[i])); i++; }
      const thead = `<thead><tr>${header.map((cell) => `<th>${inline(cell)}</th>`).join('')}</tr></thead>`;
      const tbody = `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${inline(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`;
      html.push(`<table class="md-table">${thead}${tbody}</table>`);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6);
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    if (isListItem(line)) {
      const items: string[] = [];
      while (i < lines.length && isListItem(lines[i])) {
        items.push(`<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ''))}</li>`);
        i++;
      }
      html.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    if (line.trim() === '') { i++; continue; }

    const para: string[] = [];
    while (i < lines.length && lines[i].trim() !== '' && !isHeading(lines[i]) && !isTableStart(i) && !isListItem(lines[i])) {
      para.push(inline(lines[i]));
      i++;
    }
    html.push(`<p>${para.join('<br />')}</p>`);
  }

  return html.join('');
}

export function traceName(trace: AgentTraceItem) {
  return trace.tool ?? trace.name ?? 'tool';
}
