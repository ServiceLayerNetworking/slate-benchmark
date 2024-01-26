
function wrk() {
    distribution=exp
    #distribution=norm
    thread=50
    connection=50
    duration=30

    cluster=$1
    req_type=$2
    RPS=$3
    if [ ${RPS} -lt ${connection} ]; then
        connection=${RPS}
    fi
    if [ ${connection} -lt ${thread} ]; then
        thread=${connection}
    fi

    name_tag=$4

    server_ip="http://node1.gangmuk-186812.istio-pg0.utah.cloudlab.us:32288"
    
    if [ ! -d "$name_tag" ]; then
        mkdir -p "$name_tag"
    fi

    name="${cluster}_${req_type}_${RPS}.wrklog"
    filename="${name_tag}/${name}"

    python scrape_resource_config.py > ${name_tag}/deployment_resource_${name}.txt

    echo "@@ Start ${req_type} RPS: ${RPS} to ${cluster} for ${duation} (filename: ${filename})"
    echo "@@ python scrape_resource_config.py > ${name_tag}/deployment_resource_${name}.txt"

    echo "@@ +++++++++++++++++++++++++++++++++++++++++++++++++ " > ${filename}
    echo "--------------------------------"
    echo "distribution: ${distribution}"
    echo "thread: ${thread}"
    echo "connection: ${connection}"
    echo "duration: ${duration}"
    echo "cluster: ${cluster}"
    echo "req_type: ${req_type}"
    echo "RPS: ${RPS}"
    echo "--------------------------------"

    echo "--------------------------------" >> ${filename}
    echo "distribution: ${distribution}" >> ${filename}
    echo "thread: ${thread}" >> ${filename}
    echo "connection: ${connection}" >> ${filename}
    echo "duration: ${duration}" >> ${filename}
    echo "cluster: ${cluster}" >> ${filename}
    echo "req_type: ${req_type}" >> ${filename}
    echo "RPS: ${RPS}" >> ${filename}
    echo "--------------------------------" >> ${filename}

    ./wrk -D ${distribution} -t${thread} -c${connection} -d${duration} -L -S -s ./${cluster}_${req_type}.lua ${server_ip} -R${RPS} >> ${filename}

    echo "@@ FILENAME: ${filename} written"
}

function sleep_and_print(){
    sl=$1
    echo "@@ sleep ${sl} seconds"
    sleep ${sl}
}

function restart_wasm(){
    ## Restart WasmPlugin
    kubectl delete -f wasmplugins.yaml
    echo "@@ kubectl delete -f wasmplugins.yaml"
    sleep_and_print 60

    kubectl apply -f wasmplugins.yaml
    echo "@@ kubectl apply -f wasmplugins.yaml"
    sleep_and_print 5
}

function restart_slate_controller(){
    ## Restart slate-controller deployment
    kubectl rollout restart deploy slate-controller
    echo "@@ kubectl rollout restart deploy slate-controller"
    sleep_and_print 10
}

function scp_trace_string_file(){
    tg=$1
    ## SCP trace_string.csv from slate-controller pod to the local filesystem
    slate_controller_pod=$(kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name)
    kubectl cp ${slate_controller_pod}:/app/trace_string.csv ${tg}/slate_trace_string_${tg}.slatelog
}


function full_reset(){
    tg=$1

    scp_trace_string_file $tg

    restart_wasm

    restart_slate_controller

}

start_time=$(date +%s)
cluster=west # west, east
req_type=get_metric
rps_list=(100)
tag=${req_type}_test
# restart_slate_controller
for rps in "${rps_list[@]}"; do
	per_wrk_st=$(date +%s)
	wrk ${cluster} ${req_type} ${rps} ${tag}
	#restart_wasm
	per_wrk_et=$(date +%s)
	per_wk_duration=$((per_wrk_et - per_wrk_st))
	echo "@@ per_wk_duration: ${per_wk_duration} seconds"
done
#full_reset ${tag}
scp_trace_string_file $tag
restart_slate_controller

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "@@ Duration: ${duration} seconds"
