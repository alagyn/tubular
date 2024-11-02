<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios';

import parsePath from '../path_utils.js';

let args = {}
parsePath(window.location.hash, args)

const runs = ref([])

function run_pipeline()
{
    axios.post("/api/pipelines", {
        branch: "main", // TODO
        pipeline_path: args.pipeline,
        args: {} // TODO
    })
}

function getRuns()
{
    axios.get("/api/runs?pipelinePath=" + args.pipeline)
        .then(
            (res) =>
            {
                runs.value = res.data
            }
        )
}

onMounted(() =>
{
    getRuns()
})

</script>

<template>
    <div>
        View pipeline

        <div>
            <a @click="run_pipeline" class="pure-button">Run</a>
        </div>

        <br>

        <div>
            <table class="pure-table">
                <thead>
                    <tr>
                        <th>Run</th>
                        <th>Branch</th>
                        <th>Timestamp</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="run in runs">
                        <td>{{ run.run }}</td>
                        <td>{{ run.branch }}</td>
                        <td>{{ run.timestamp }}</td>
                        <td>{{ run.duration }}</td>
                        <td>{{ run.status }}</td>
                    </tr>
                </tbody>

            </table>
        </div>
    </div>
</template>