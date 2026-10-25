class Greeter(private val names: List<String>?) {
    fun greetAll(): String = names!!.map { "Hello, " + it }.joinToString("\n")
}
