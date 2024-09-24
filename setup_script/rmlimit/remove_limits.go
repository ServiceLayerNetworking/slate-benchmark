package main

import (
	"context"
	"flag"
	"fmt"
	"path/filepath"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	// resource "k8s.io/apimachinery/pkg/api/resource"
)

func main() {
	// Load the kubeconfig file (assumes you have kubeconfig available)
	kubeconfig := filepath.Join("/users/gangmuk", ".kube", "config")
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		panic(err.Error())
	}

	// Create the clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	// Get all deployments in the default namespace
	deploymentsClient := clientset.AppsV1().Deployments(corev1.NamespaceDefault)
	deployments, err := deploymentsClient.List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		panic(err.Error())
	}

	// Iterate through deployments and add resource limits
	for _, deployment := range deployments.Items {
		if deployment.Name == "slate-controller" {
			continue
		}
		containers := deployment.Spec.Template.Spec.Containers
		containers[0].Resources.Limits = corev1.ResourceList{
			corev1.ResourceCPU: resource.MustParse("200"),
		}
		// Add resource limits for each container in the deployment
		// for i := range containers {
		// 	// Define resource limits (2000 millicores)
		// 	// limits := corev1.ResourceList{
		// 	// 	corev1.ResourceCPU: resource.MustParse("200m"),
		// 	// }
		// 	containers[i].Resources.Limits = nil
		// 	// containers[i].Resources.Limits = limits
		// }

		// Update the deployment with the modified containers
		_, err := deploymentsClient.Update(context.TODO(), &deployment, metav1.UpdateOptions{})
		if err != nil {
			fmt.Printf("Failed to update deployment %s: %v\n", deployment.Name, err)
		} else {
			fmt.Printf("Updated deployment %s to set resource limits to 2000 millicores\n", deployment.Name)
		}
	}
}

// homeDir returns the user's home directory
func homeDir() string {
	if h := flag.Lookup("HOME"); h != nil {
		return h.Value.String()
	}
	return "~"
}
