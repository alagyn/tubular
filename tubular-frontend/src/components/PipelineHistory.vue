<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios';

import parsePath from '../path_utils.js';
import { STATUS_TO_NAME, STATUS_TO_STYLE } from '@/enums.js';

let args = {}
parsePath(window.location.hash, args)

const runPath = `#/view_run?pipeline=${args.pipeline}`

const runs = ref([])

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

let getRunsInterval = 0

onMounted(() =>
{
    getRuns()
    getRunsInterval = window.setInterval(getRuns, 4000)
})

onUnmounted(() =>
{
    window.clearInterval(getRunsInterval)
})

</script>

<template>
    <div>
        View pipeline

        <div>
            <a :href="'#/run_pipeline?pipeline=' + args.pipeline" class="pure-button">New Run</a>
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
                        <td><a class="pure-button" :href="runPath + `&branch=${run.branch}&run=${run.run}`">{{ run.run
                                }}</a></td>
                        <td>{{ run.branch }}</td>
                        <td>{{ run.timestamp }}</td>
                        <td>{{ run.duration }}</td>
                        <td :class="STATUS_TO_STYLE[run.status]">{{ STATUS_TO_NAME[run.status] }}</td>
                    </tr>
                </tbody>

            </table>
        </div>
    </div>
</template>

<style></style>