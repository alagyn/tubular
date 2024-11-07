<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios';

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
    Pipelines

    <div>
      <div v-if="pipelines.length == 0">Loading</div>
      <table v-else class="pure-table">
        <tbody>
          <tr v-for="p in pipelines">
            <!-- TODO change color based on status -->
            <td>
              <a :href="'#/view_pipeline?pipeline=' + p.path" class="button-small pure-button">{{ p.name
                }}</a>
            </td>
            <td>{{ p.path }}</td>
            <td>{{ p.timestamp }}</td>
            <td>{{ p.status }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>