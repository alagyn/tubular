<script setup lang=js>
import { ref, onMounted } from 'vue'
import axios from 'axios';
import { Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, Title } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend, Title)

const labels = ["Idle", "Active", "Offline"]

const nodeStatus = ref({
    datasets: [{
        data: [0, 0, 0]
    }]
})

const graphOptions = {
    plugins: {
        title: {
            display: true,
            text: "Node Status",
        },
    },
    responsive: true,
    backgroundColor: ["#0ecf16", "#0ec0cf", "#eb0037"],
    radius: "75%"
}


function getNodeStatus()
{
    axios.get("/api/node_status").then(
        (response) =>
        {
            let idle = 0
            let running = 0
            let offline = 0

            for (let key in response.data)
            {
                let status = response.data[key]
                console.log(key + " " + status)
                if (status == "Idle")
                {
                    ++idle
                }
                else if (status == "Active")
                {
                    ++running
                }
                else
                {
                    ++offline
                }
            }

            nodeStatus.value = {
                labels: labels,

                datasets: [{
                    data: [idle, running, offline]
                }]
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
    <Doughnut :data="nodeStatus" :options="graphOptions" />
</template>