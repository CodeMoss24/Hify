import { get, post, put, del } from '@/api'
import type { PageResult, PageParams } from '@/types/api'
import type { KnowledgeBase, Document, DocumentChunk } from '@/types/model'

// ── Knowledge Base ──────────────────────────────────────────

export function getKnowledgeBaseList(params: PageParams & { name?: string }): Promise<PageResult<KnowledgeBase>> {
  return get('/v1/knowledge-bases', params)
}

export function createKnowledgeBase(data: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
  return post('/v1/knowledge-bases', data)
}

export function updateKnowledgeBase(id: number, data: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
  return put(`/v1/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id: number): Promise<void> {
  return del(`/v1/knowledge-bases/${id}`)
}

// ── Document ───────────────────────────────────────────────

export function getDocumentList(kbId: number, params: PageParams): Promise<PageResult<Document>> {
  return get(`/v1/knowledge-bases/${kbId}/documents`, params)
}

export function uploadDocument(kbId: number, formData: FormData): Promise<Document> {
  return post(`/v1/knowledge-bases/${kbId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDocument(id: number): Promise<Document> {
  return get(`/v1/documents/${id}`)
}

export function getDocumentChunks(id: number, params: PageParams): Promise<PageResult<DocumentChunk>> {
  return get(`/v1/documents/${id}/chunks`, params)
}

export function deleteDocument(id: number): Promise<void> {
  return del(`/v1/documents/${id}`)
}
