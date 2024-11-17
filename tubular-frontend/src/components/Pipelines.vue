<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios';
import { STATUS_TO_STYLE, STATUS_TO_NAME } from '../enums.js';

const pipelines = ref([])

function getPipelines(branch)
{
  let args = {}
  if (branch.length > 0)
  {
    args.branch = branch
  }

  axios.get("/api/pipelines", args).then((res) =>
  {
    pipelines.value = res.data
  })
}

onMounted(() =>
{
  getPipelines("")
})

</script>

<template>
  <div>
    <div>
      <div v-if="pipelines.length == 0">Loading</div>
      <table v-else class="pure-table pure-table-bordered">
        <tbody>
          <tr v-for="p in pipelines">
            <!-- TODO change color based on status -->
            <td>
              <a :href="'#/view_pipeline?pipeline=' + p.path" class="button-small pure-button tubular-button">{{ p.name
                }}</a>
            </td>
            <td>{{ p.path }}</td>
            <td>{{ p.timestamp }}</td>
            <td :class="STATUS_TO_STYLE[p.status]">{{ STATUS_TO_NAME[p.status] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>