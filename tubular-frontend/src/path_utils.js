export default function parsePath(path, argsOut)
{
    console.log(path)
    let questionPos = path.search("\\?")
    console.log("questionPos: " + questionPos)

    let route = ""
    if(questionPos > 0)
    {
        route = path.substr(0, questionPos)
    }
    else
    {
        route = path
    }

    // cut off #
    route = route.substring(1)

    let args = path.substr(questionPos + 1)

    if (args.length > 0)
    {
        let argStrs = args.split("&")
        for (const arg of argStrs)
        {
            let equalPos = arg.search("=")
            let argName = arg.substr(0, equalPos)
            let argValue = arg.substr(equalPos + 1)
            argsOut[argName] = argValue
        }
    }

    console.log("route: " + route)

    return route
}