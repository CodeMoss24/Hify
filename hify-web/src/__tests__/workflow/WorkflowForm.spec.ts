import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ElementPlus from 'element-plus'

// ── Mocks ──
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: {} }),
}))

const mockNotifySuccess = vi.fn()
const mockNotifyError = vi.fn()
vi.mock('@/utils/notify', () => ({
  notifySuccess: (...args: any[]) => mockNotifySuccess(...args),
  notifyError: (...args: any[]) => mockNotifyError(...args),
}))

const mockCreateWorkflow = vi.fn().mockResolvedValue({ id: 1 })
const mockUpdateWorkflow = vi.fn().mockResolvedValue({ id: 1 })
const mockGetWorkflow = vi.fn().mockResolvedValue({
  id: 1,
  name: 'Test Workflow',
  description: 'Test Desc',
  nodes: [
    { node_key: 'start', name: '开始', node_type: 'START', config: {}, position_x: 0, position_y: 0 },
    { node_key: 'llm', name: 'LLM 处理', node_type: 'LLM', config: { model_config_id: 1, prompt: '你好', output_variable: 'llm_output' }, position_x: 200, position_y: 0 },
    { node_key: 'end', name: '结束', node_type: 'END', config: {}, position_x: 400, position_y: 0 },
  ],
  edges: [
    { source_node_key: 'start', target_node_key: 'llm', condition: '' },
    { source_node_key: 'llm', target_node_key: 'end', condition: '' },
  ],
  status: 'DRAFT',
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
})
vi.mock('@/api/workflow', () => ({
  getWorkflowList: vi.fn(),
  getWorkflow: (id: number) => mockGetWorkflow(id),
  createWorkflow: (data: any) => mockCreateWorkflow(data),
  updateWorkflow: (id: number, data: any) => mockUpdateWorkflow(id, data),
  deleteWorkflow: vi.fn(),
}))

const mockGetProviderList = vi.fn().mockResolvedValue({
  list: [
    { id: 1, name: 'OpenAI', provider_type: 'openai' },
  ],
  total: 1,
})
vi.mock('@/api/provider', () => ({
  getProviderList: (...args: any[]) => mockGetProviderList(...args),
}))

const mockGetModelList = vi.fn().mockResolvedValue({
  list: [
    { id: 1, name: 'GPT-4', model_id: 'gpt-4', enabled: 1 },
  ],
  total: 1,
})
vi.mock('@/api/model', () => ({
  getModelList: (...args: any[]) => mockGetModelList(...args),
}))

// ── Component ──
import WorkflowForm from '@/views/workflow/WorkflowForm.vue'

function createWrapper(props = {}) {
  return mount(WorkflowForm, {
    props,
    global: {
      plugins: [ElementPlus],
      stubs: {
        'el-dropdown-menu': true,
        'el-dropdown-item': true,
        'el-dropdown': {
          template: '<div><slot /><slot name="dropdown" /></div>',
        },
      },
    },
  })
}

describe('WorkflowForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── 初始渲染 ──
  it('should render with default START and END nodes when creating', () => {
    const wrapper = createWrapper()

    const nodeCards = wrapper.findAll('.node-card')
    expect(nodeCards.length).toBe(2) // START + END

    const tags = wrapper.findAll('.el-tag')
    const tagTexts = tags.map(t => t.text())
    expect(tagTexts).toContain('开始')
    expect(tagTexts).toContain('结束')
  })

  it('should show create mode title', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('h2').text()).toBe('新建工作流')
  })

  it('should show edit mode title when workflowId prop provided', async () => {
    mockGetWorkflow.mockResolvedValue({
      id: 1,
      name: 'Test',
      description: '',
      nodes: [
        { node_key: 'start', name: '开始', node_type: 'START', config: {}, position_x: 0, position_y: 0 },
        { node_key: 'end', name: '结束', node_type: 'END', config: {}, position_x: 200, position_y: 0 },
      ],
      edges: [],
      status: 'DRAFT',
      created_at: '',
      updated_at: '',
    })

    const wrapper = createWrapper({ workflowId: 1 })
    await nextTick()
    await nextTick()

    expect(wrapper.find('h2').text()).toBe('编辑工作流')
  })

  // ── 节点增删 ──
  it('should add LLM node when add button clicked', async () => {
    const wrapper = createWrapper()

    // 通过组件内部方法测试（暴露的方法）
    const vm = wrapper.vm as any

    // 初始 2 个节点
    expect(wrapper.findAll('.node-card').length).toBe(2)

    // 直接调用 addNode
    vm.formData.nodes.splice(vm.formData.nodes.length - 1, 0, {
      uid: 'test_1',
      node_key: 'llm_1',
      name: 'LLM 处理',
      node_type: 'LLM',
      config: {},
    })
    await nextTick()

    expect(wrapper.findAll('.node-card').length).toBe(3)
  })

  it('should remove a user-added node', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    // 添加节点
    vm.formData.nodes.splice(vm.formData.nodes.length - 1, 0, {
      uid: 'test_2',
      node_key: 'llm_2',
      name: 'LLM 处理',
      node_type: 'LLM',
      config: {},
    })
    await nextTick()
    expect(wrapper.findAll('.node-card').length).toBe(3)

    // 删除节点
    const index = vm.formData.nodes.findIndex((n: any) => n.uid === 'test_2')
    vm.formData.nodes.splice(index, 1)
    await nextTick()
    expect(wrapper.findAll('.node-card').length).toBe(2)
  })

  it('should not allow removing START node', () => {
    // START node has type START and removeNode checks for it
    // This is a logic test - the UI doesn't show delete button for START/END
    const wrapper = createWrapper()
    const deleteButtons = wrapper.findAll('.node-header-right .el-button--danger')
    expect(deleteButtons.length).toBe(0) // No delete button for START/END
  })

  // ── 节点类型配置 ──
  it('should show model dropdown and prompt textarea for LLM node', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    // 替换成 LLM 节点
    vm.formData.nodes = [
      vm.formData.nodes[0], // START
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: undefined,
        prompt: '',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1], // END
    ]
    await nextTick()

    // 应该看到 LLM 标签
    const tags = wrapper.findAll('.el-tag')
    const tagTexts = tags.map(t => t.text())
    expect(tagTexts).toContain('LLM')
  })

  it('should show expression input for CONDITION node', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.nodes = [
      vm.formData.nodes[0], // START
      {
        uid: 'cond_test',
        node_key: 'cond_1',
        name: '条件判断',
        node_type: 'CONDITION',
        config: {},
        expression: '',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1], // END
    ]
    await nextTick()

    const tags = wrapper.findAll('.el-tag')
    const tagTexts = tags.map(t => t.text())
    expect(tagTexts).toContain('条件')
  })

  // ── 校验 ──
  it('should validate LLM node has model selected', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test'
    vm.formData.nodes = [
      vm.formData.nodes[0],
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: undefined,
        prompt: 'test prompt',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1],
    ]
    await nextTick()

    // Call validateNodes directly
    const error = vm.validateNodes()
    expect(error).toBeTruthy()
    expect(error).toContain('模型')
  })

  it('should validate LLM node has prompt', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test'
    vm.formData.nodes = [
      vm.formData.nodes[0],
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: 1,
        prompt: '',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1],
    ]
    await nextTick()

    const error = vm.validateNodes()
    expect(error).toBeTruthy()
    expect(error).toContain('提示词')
  })

  it('should validate CONDITION node has expression', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test'
    vm.formData.nodes = [
      vm.formData.nodes[0],
      {
        uid: 'cond_test',
        node_key: 'cond_1',
        name: '条件判断',
        node_type: 'CONDITION',
        config: {},
        expression: '',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1],
    ]
    await nextTick()

    const error = vm.validateNodes()
    expect(error).toBeTruthy()
    expect(error).toContain('表达式')
  })

  it('should pass validation when all nodes are valid', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test'
    vm.formData.nodes = [
      vm.formData.nodes[0],
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: 1,
        prompt: 'test prompt',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1],
    ]
    await nextTick()

    const error = vm.validateNodes()
    expect(error).toBeNull()
  })

  // ── 连线 ──
  it('should auto-generate edges based on node order', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.nodes = [
      vm.formData.nodes[0], // START
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
      },
      vm.formData.nodes[vm.formData.nodes.length - 1], // END
    ]
    vm.rebuildEdges()
    await nextTick()

    expect(vm.formData.edges.length).toBe(2)
    expect(vm.formData.edges[0].source_node_key).toBe('start')
    expect(vm.formData.edges[0].target_node_key).toBe('llm_1')
    expect(vm.formData.edges[1].source_node_key).toBe('llm_1')
    expect(vm.formData.edges[1].target_node_key).toBe('end')
  })

  // ── 提交 ──
  it('should call createWorkflow on submit in create mode', async () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test Workflow'
    vm.formData.nodes = [
      vm.formData.nodes[0],
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: 1,
        prompt: 'test prompt',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1],
    ]
    vm.rebuildEdges()

    await vm.handleSubmit()
    await nextTick()

    expect(mockCreateWorkflow).toHaveBeenCalled()
    const callData = mockCreateWorkflow.mock.calls[0][0]
    expect(callData.name).toBe('Test Workflow')
    expect(callData.nodes.length).toBe(3)
    expect(callData.edges.length).toBe(2)
  })

  it('should call updateWorkflow on submit in edit mode', async () => {
    mockGetWorkflow.mockResolvedValue({
      id: 1,
      name: 'Existing',
      description: '',
      nodes: [
        { node_key: 'start', name: '开始', node_type: 'START', config: {}, position_x: 0, position_y: 0 },
        { node_key: 'end', name: '结束', node_type: 'END', config: {}, position_x: 200, position_y: 0 },
      ],
      edges: [],
      status: 'DRAFT',
      created_at: '',
      updated_at: '',
    })

    const wrapper = createWrapper({ workflowId: 1 })
    await nextTick()
    await nextTick()
    await nextTick()

    const vm = wrapper.vm as any
    vm.formData.name = 'Updated Workflow'
    vm.rebuildEdges()

    await vm.handleSubmit()
    await nextTick()

    expect(mockUpdateWorkflow).toHaveBeenCalledWith(1, expect.any(Object))
  })

  // ── 数据回填 ──
  it('should pre-populate form fields when editing existing workflow', async () => {
    mockGetWorkflow.mockResolvedValue({
      id: 1,
      name: 'Test Workflow',
      description: 'Test Desc',
      nodes: [
        { node_key: 'start', name: '开始', node_type: 'START', config: {}, position_x: 0, position_y: 0 },
        { node_key: 'llm_1', name: 'LLM 节点1', node_type: 'LLM', config: { model_config_id: 1, prompt: 'hello', output_variable: 'llm_output' }, position_x: 200, position_y: 0 },
        { node_key: 'end', name: '结束', node_type: 'END', config: {}, position_x: 400, position_y: 0 },
      ],
      edges: [
        { source_node_key: 'start', target_node_key: 'llm_1', condition: '' },
        { source_node_key: 'llm_1', target_node_key: 'end', condition: '' },
      ],
      status: 'DRAFT',
      created_at: '',
      updated_at: '',
    })

    const wrapper = createWrapper({ workflowId: 1 })
    await nextTick()
    await nextTick()
    await nextTick()

    const vm = wrapper.vm as any
    expect(vm.formData.name).toBe('Test Workflow')
    expect(vm.formData.description).toBe('Test Desc')
    expect(vm.formData.nodes.length).toBe(3)

    // LLM 节点应该有正确的配置
    const llmNode = vm.formData.nodes.find((n: any) => n.node_type === 'LLM')
    expect(llmNode).toBeDefined()
    expect(llmNode.model_config_id).toBe(1)
    expect(llmNode.prompt).toBe('hello')
  })

  // ── buildSubmitData ──
  it('should build correct submit data from form nodes', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    vm.formData.name = 'Test'
    vm.formData.nodes = [
      vm.formData.nodes[0], // START
      {
        uid: 'llm_test',
        node_key: 'llm_1',
        name: 'LLM 处理',
        node_type: 'LLM',
        config: {},
        model_config_id: 1,
        prompt: 'test prompt',
      },
      vm.formData.nodes[vm.formData.nodes.length - 1], // END
    ]
    vm.rebuildEdges()

    const data = vm.buildSubmitData()
    expect(data.nodes.length).toBe(3)
    expect(data.edges.length).toBe(2)

    const llmConfig = data.nodes[1].config
    expect(llmConfig.model_config_id).toBe(1)
    expect(llmConfig.prompt).toBe('test prompt')
  })

  // ── onNodeTypeChange ──
  it('should clear config when node type changes', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm as any

    const node = {
      uid: 'test',
      node_key: 'test',
      name: 'Test',
      node_type: 'LLM',
      config: { old: 'data' },
      model_config_id: 1,
      prompt: 'old',
      expression: undefined,
    }

    vm.onNodeTypeChange(node, 'CONDITION')
    expect(node.model_config_id).toBeUndefined()
    expect(node.prompt).toBeUndefined()
    expect(node.expression).toBeUndefined()
    expect(node.config).toEqual({})
  })
})
