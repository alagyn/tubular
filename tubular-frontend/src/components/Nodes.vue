<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios';

const nodes = ref([]);

function getNodeStatus()
{
    axios.get("/api/node_status").then(
        (response) =>
        {
            nodes.value = []
            for (let key in response.data)
            {
                nodes.value.push({ name: key, status: response.data[key] });
            }
        }
    )
}

onMounted(() =>
{
    getNodeStatus()
})

</script>

<template>
    <div>
        <h1>Nodes</h1>
        <a class="pure-button pure-button-primary" @click="getNodeStatus">Refresh</a>
    </div>
    <br />
    <div>
        <table class="pure-table nodetable">
            <thead>
                <tr>
                    <th>Node</th>
                    <th>Status</th>
                    <th>Task</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="node in nodes">
                    <td>{{ node.name }}</td>
                    <td>{{ node.status }} </td>
                    <td></td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<style scoped></style>