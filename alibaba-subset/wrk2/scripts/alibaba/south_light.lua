local socket = require("socket")
math.randomseed(socket.gettime()*1000)
math.random(); math.random(); math.random()

local url = "http://node2.gangmuk-184284.istio-pg0.clemson.cloudlab.us:32340"

local function light()
  local method = "POST"
  local path = url .. "/light"

  local headers = {}
  headers["x-slate-destination"] = "south"
  return wrk.format(method, path, headers, nil)
end

request = function()
  return light(url)
end
