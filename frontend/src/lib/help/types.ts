export interface HelpEntry {
  id: string;
  title: string;
  route: string;
  path: string;
  tab?: string;
  role: string;
  module: string;
  description: string;
  fullReferencePath: string;
  quickGuidePath?: string;
  screenshotFile?: string;
  moduleManualPath?: string;
  keywords: string[];
}
