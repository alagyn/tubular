<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios';

import parsePath from '../path_utils.js';

let args = {}
parsePath(window.location.hash, args)

const pipelineArgs = ref([])
const branches = ref([])
const selectedBranch = ref("")

function getArgs()
{
    // TODO branch
    axios.get("/api/pipeline?pipelinePath=" + args.pipeline + "&branch=main").then(
        (res) =>
        {
            pipelineArgs.value = res.data
        }
    )
}

function getBranches()
{
    axios.get("/api/branches").then((res) =>
    {
        branches.value = res.data
        selectedBranch.value = branches[0]
    })
}


function run_pipeline()
{
    axios.post("/api/pipelines", {
        branch: selectedBranch.value,
        pipeline_path: args.pipeline,
        args: pipelineArgs.value
    }).then((res) =>
    {
        window.location.hash = "#/view_pipeline?pipeline=" + args.pipeline
    })
}

onMounted(() =>
{
    getArgs()
    getBranches()
})

</script>

<template>
    <div>
        Run Pipeline

        <div>
            <button @click="run_pipeline()" class="pure-button">Run</button>
            <form class="pure-form pure-form-stacked">
                <fieldset>
                    <label for="branch-select">Pipeline Branch</label>
                    <select id="branch-select" class="pure-input-1-2" v-model="selectedBranch">
                        <option v-for="branch in branches">
                            {{ branch }}
                        </option>
                    </select>
                    <div v-for="arg in pipelineArgs">
                        <label :for="arg.k + '_input'">{{ arg.k }}</label>
                        <input type="text" :id="arg.k + '_input'" class="pure-u-23-24" v-model="arg.v" />
                    </div>
                </fieldset>
            </form>
        </div>
    </div>
</template>