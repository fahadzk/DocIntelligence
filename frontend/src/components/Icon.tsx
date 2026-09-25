import {
  AddRegular, ArrowClockwiseRegular, ArrowDownloadRegular, ArrowSortRegular,
  ArrowUploadRegular, BeakerRegular, BookOpenRegular, BrainCircuitRegular,
  CheckmarkCircleRegular, ChevronDownRegular, ChevronLeftRegular,
  ChevronRightRegular, ChevronUpRegular, CopyRegular,
  DatabaseRegular, DeleteRegular, DesktopRegular, DocumentRegular,
  EditRegular, ErrorCircleRegular, FilterRegular, FolderRegular,
  HomeRegular, InfoRegular, LinkRegular, OpenRegular, PanelLeftContractRegular,
  PanelLeftExpandRegular, PinRegular, QuestionCircleRegular,
  SearchRegular, SettingsRegular, TextBulletListRegular, WarningRegular,
  WeatherMoonRegular, WeatherSunnyRegular,
} from "@fluentui/react-icons";

const glyphs = {
  add: AddRegular, ask: QuestionCircleRegular, book: BookOpenRegular,
  check: CheckmarkCircleRegular, chevronDown: ChevronDownRegular,
  chevronLeft: ChevronLeftRegular, chevronRight: ChevronRightRegular,
  chevronUp: ChevronUpRegular, chunk: TextBulletListRegular, copy: CopyRegular,
  dark: WeatherMoonRegular, database: DatabaseRegular, delete: DeleteRegular,
  document: DocumentRegular, download: ArrowDownloadRegular, edit: EditRegular,
  embedding: BrainCircuitRegular, error: ErrorCircleRegular, filter: FilterRegular,
  lab: BeakerRegular, light: WeatherSunnyRegular, link: LinkRegular,
  open: OpenRegular, overview: HomeRegular, project: FolderRegular,
  refresh: ArrowClockwiseRegular, search: SearchRegular, settings: SettingsRegular,
  sort: ArrowSortRegular, system: DesktopRegular, upload: ArrowUploadRegular,
  warning: WarningRegular, info: InfoRegular, model: BrainCircuitRegular,
  vector: DatabaseRegular, retrieval: SearchRegular,
  rerank: ArrowSortRegular,
  panelContract: PanelLeftContractRegular, panelExpand: PanelLeftExpandRegular,
  pin: PinRegular,
} as const;

export type IconName = keyof typeof glyphs;

export function Icon({ name, size = 18, className = "" }: { name: IconName; size?: number; className?: string }) {
  const Glyph = glyphs[name];
  return <Glyph aria-hidden="true" focusable="false" fontSize={size} className={`app-icon ${className}`} />;
}
