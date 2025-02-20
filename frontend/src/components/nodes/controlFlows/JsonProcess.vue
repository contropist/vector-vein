<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { AddOne, ReduceOne, Edit } from '@icon-park/vue-next'
import BaseNode from '@/components/nodes/BaseNode.vue'
import BaseField from '@/components/nodes/BaseField.vue'
import { createTemplateData } from './JsonProcess'


const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
})

const { t } = useI18n()

const fieldsData = ref(props.data.template)
const templateData = createTemplateData()
Object.entries(templateData.template).forEach(([key, value]) => {
  fieldsData.value[key] = fieldsData.value[key] || value
  if (value.is_output) {
    fieldsData.value[key].is_output = true
  }
})

const showKeyDrawer = ref(false)
const editKeyData = reactive({
  index: -1,
  value: ''
})

const removeKey = (index) => {
  fieldsData.value.keys.value.splice(index, 1)
}

const editKey = (index) => {
  editKeyData.index = index
  editKeyData.value = fieldsData.value.keys.value[index]
  showKeyDrawer.value = true
}

const saveKey = () => {
  if (editKeyData.index === -1) {
    fieldsData.value.keys.value.push(editKeyData.value)
  } else {
    fieldsData.value.keys.value[editKeyData.index] = editKeyData.value
  }
  showKeyDrawer.value = false
  editKeyData.index = -1
  editKeyData.value = ''
}

const addKey = () => {
  editKeyData.index = -1
  editKeyData.value = ''
  showKeyDrawer.value = true
}
</script>

<template>
  <BaseNode :nodeId="id" :debug="props.data.debug" :fieldsData="fieldsData"
    translatePrefix="components.nodes.controlFlows.JsonProcess"
    documentPath="/help/docs/control-flows#node-JsonProcess">
    <template #main>
      <a-flex vertical gap="small">
        <BaseField :name="t('components.nodes.common.input')" required type="target" v-model:data="fieldsData.input">
          <a-textarea class="nodrag" v-model:value="fieldsData.input.value" :autoSize="{ minRows: 1, maxRows: 10 }"
            :showCount="true" :placeholder="fieldsData.input.placeholder" />
        </BaseField>

        <BaseField :name="t('components.nodes.controlFlows.JsonProcess.process_mode')" required type="target"
          v-model:data="fieldsData.process_mode">
          <a-select style="width: 100%;" v-model:value="fieldsData.process_mode.value"
            :options="fieldsData.process_mode.options" />
        </BaseField>

        <template v-if="fieldsData.process_mode.value == 'get_value'">
          <BaseField :name="t('components.nodes.controlFlows.JsonProcess.key')" required type="target"
            v-model:data="fieldsData.key">
            <a-input class="nodrag" v-model:value="fieldsData.key.value" :placeholder="fieldsData.key.placeholder" />
          </BaseField>

          <BaseField :name="t('components.nodes.controlFlows.JsonProcess.default_value')" type="target"
            v-model:data="fieldsData.default_value">
            <a-input class="nodrag" v-model:value="fieldsData.default_value.value"
              :placeholder="fieldsData.default_value.placeholder" />
          </BaseField>
        </template>

        <template v-if="fieldsData.process_mode.value == 'get_multiple_values'">
          <BaseField :name="t('components.nodes.controlFlows.JsonProcess.keys')" required type="target"
            v-model:data="fieldsData.keys">
            <a-flex vertical gap="small">
              <a-space v-for="(key, index) in fieldsData.keys.value" :key="index">
                <a-typography-text>{{ key }}</a-typography-text>
                <a-button type="text" @click="editKey(index)">
                  <template #icon>
                    <Edit class="clickable-icon" />
                  </template>
                </a-button>
                <a-button type="text" @click="removeKey(index)">
                  <template #icon>
                    <ReduceOne class="clickable-icon" fill="#ff4d4f" />
                  </template>
                </a-button>
              </a-space>
              <a-button block type="dashed" @click="addKey">
                <template #icon>
                  <AddOne />
                </template>
                {{ t('components.nodes.controlFlows.JsonProcess.add_key') }}
              </a-button>
            </a-flex>
          </BaseField>

          <BaseField :name="t('components.nodes.controlFlows.JsonProcess.default_value')" type="target"
            v-model:data="fieldsData.default_value">
            <a-input class="nodrag" v-model:value="fieldsData.default_value.value"
              :placeholder="fieldsData.default_value.placeholder" />
          </BaseField>
        </template>
      </a-flex>
    </template>
    <template #output>
      <a-flex vertical style="width: 100%;">
        <BaseField v-if="fieldsData.process_mode.value != 'get_multiple_values'" v-model:data="fieldsData.output"
          :name="t('components.nodes.common.output')" type="source" nameOnly>
        </BaseField>
        <template v-else>
          <BaseField v-for="(key, index) in fieldsData.keys.value" :key="index" :name="key" type="source" nameOnly
            :data="{ name: `output-${key}` }">
          </BaseField>
        </template>
      </a-flex>
    </template>
  </BaseNode>

  <a-drawer v-model:open="showKeyDrawer"
    :title="t(`components.nodes.controlFlows.JsonProcess.${editKeyData.index === -1 ? 'add' : 'edit'}_key`)"
    placement="right">
    <template #extra>
      <a-button type="primary" @click="saveKey">
        {{ t(editKeyData.index === -1 ? 'common.add' : 'common.save') }}
      </a-button>
    </template>
    <a-form>
      <a-form-item :label="t('components.nodes.controlFlows.JsonProcess.key')">
        <a-input v-model:value="editKeyData.value" />
      </a-form-item>
    </a-form>
  </a-drawer>
</template>