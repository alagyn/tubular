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
            console.log(response)
            console.log(response.data)
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
    <div>Nodes</div>
    <div>
        <a class="pure-button" @click="getNodeStatus">Refresh</a>
        <ul>
            <li v-for="node in nodes">
                {{ node.name }}: {{ node.status }}
            </li>
        </ul>

    </div>
</template>