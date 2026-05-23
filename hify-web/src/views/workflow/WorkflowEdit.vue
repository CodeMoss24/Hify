<template>
  <WorkflowForm :workflow-id="Number(route.params.id as string)" />
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import WorkflowForm from './WorkflowForm.vue'

const route = useRoute()
</script>
