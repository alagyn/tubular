<script setup lang=js>
import { ref, onMounted } from 'vue'
import axios from 'axios';
import { Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, Title } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend, Title)

const labels = ["Error", "Fail", "Running", "Queued", "Success"]

const runData = ref({
    datasets: [{
        data: []
    }]
})

const graphOptions = {
    plugins: {
        title: {
            display: true,
            text: "Run Status",
        },
    },
    responsive: true,
    backgroundColor: ["#eb0037", "#eb9700", "#2864d7", "#0ec0cf", "#25da30"],
    radius: "75%"
}


function getRunStats()
{
    axios.get("/api/runs_stats").then(
        (response) =>
        {
            let res = response.data
            runData.value = {
                labels: labels,

                datasets: [{
                    data: [res.runs.error, res.runs.fail, res.runs.running, res.runs.queued, res.runs.success]
                }]
            }
        }
    )
}

onMounted(() =>
{
    getRunStats()
})
</script>

<template>
    <Doughnut :data="runData" :options="graphOptions" />
</template>