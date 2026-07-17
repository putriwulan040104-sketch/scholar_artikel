import type * as d3 from "d3";
import type { ArticleRelationType, ReferenceMatch } from "@/api/api";

export type GraphNode = d3.SimulationNodeDatum & {
  id: number;
  articleId?: number | null;
  title?: string | null;
  year?: number | null;
  doi?: string | null;
  authors?: string[] | string | null;
  referenceCount?: number;
  degree: number;
};

export type GraphLink = d3.SimulationLinkDatum<GraphNode> & {
  source: number | string | GraphNode;
  target: number | string | GraphNode;
  weight: number;
  sharedReferences: string[];
  sharedReferenceMatches: ReferenceMatch[];
  sharedKeywords: string[];
  sharedAuthors: string[];
  relationType?: ArticleRelationType | string | null;
};

export type GraphModel = {
  gNodes: GraphNode[];
  gLinks: GraphLink[];
  degreeById: Map<number, number>;
  inDegreeById: Map<number, number>;
  outDegreeById: Map<number, number>;
};

export type GraphRelation = {
  node: GraphNode;
  weight: number;
  sharedReferences: string[];
  sharedReferenceMatches: ReferenceMatch[];
  sharedKeywords: string[];
  sharedAuthors: string[];
  relationType?: ArticleRelationType | string | null;
};

export type SelectedRelations = {
  connected: GraphRelation[];
};

export type StoredFilters = {
  yearStart?: string;
  yearEnd?: string;
  jenisArtikel?: string;
  jenisAnalisis?: string;
  kategori?: string;
  jumlahKemunculan?: string;
};

export type QueryArticleLite = {
  id: number;
  title?: string | null;
  authors?: string[] | string | null;
  year?: number | null;
  doi?: string | null;
};

export type FavoriteItem = {
  id: number;
  title: string;
  authors: string;
  year?: number;
  similarity_score: number;
  pdf_url?: string | null;
  url?: string | null;
  access_url?: string | null;
  is_pdf?: boolean | string;
};

export type GraphTooltip = {
  visible: boolean;
  x: number;
  y: number;
  title: string;
  authors: string;
  year: string;
  relations: number;
  references: number;
};
